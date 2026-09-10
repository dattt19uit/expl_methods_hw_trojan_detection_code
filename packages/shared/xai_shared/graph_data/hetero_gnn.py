"""
Heterogeneous Graph Neural Network for Hardware Trojan Detection.

Designed specifically for bipartite gate-level netlists (cell <-> net) with
typed edges distinguishing data inputs, control inputs, and gate outputs.
"""

from typing import Dict, List, Optional, Tuple, Union
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import HeteroConv, SAGEConv, GATv2Conv, Linear


class HeteroTrojanGNN(nn.Module):
    """
    Heterogeneous GNN for cell node binary classification (Trojan vs Benign).
    """

    def __init__(
        self,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        conv_type: str = 'sage',
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout = dropout
        self.conv_type = conv_type

        # Initial linear projections for cell and net input features
        self.cell_in = Linear(-1, hidden_dim)
        self.net_in = Linear(-1, hidden_dim)

        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()

        edge_types = [
            ('net', 'data_input', 'cell'),
            ('net', 'control_input', 'cell'),
            ('cell', 'outputs', 'net'),
            ('cell', 'rev_data_input', 'net'),
            ('cell', 'rev_control_input', 'net'),
            ('net', 'rev_outputs', 'cell'),
        ]

        for _ in range(num_layers):
            conv_dict = {}
            for et in edge_types:
                if conv_type == 'gat':
                    conv_dict[et] = GATv2Conv(hidden_dim, hidden_dim, add_self_loops=False)
                else:
                    conv_dict[et] = SAGEConv((hidden_dim, hidden_dim), hidden_dim)
            self.convs.append(HeteroConv(conv_dict, aggr='sum'))
            self.norms.append(nn.ModuleDict({
                'cell': nn.LayerNorm(hidden_dim),
                'net': nn.LayerNorm(hidden_dim),
            }))

        # Classifier head for cell nodes
        self.classifier = nn.Sequential(
            Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            Linear(hidden_dim // 2, 1),
        )

    def forward(
        self,
        x_dict: Dict[str, torch.Tensor],
        edge_index_dict: Dict[Tuple[str, str, str], torch.Tensor],
    ) -> torch.Tensor:
        """
        Forward pass returning unnormalized logits for cell nodes.
        Shape: [num_cells, 1]
        """
        # Project heterogeneous node features to shared hidden_dim
        h_dict = {
            'cell': F.relu(self.cell_in(x_dict['cell'])),
            'net': F.relu(self.net_in(x_dict['net'])),
        }

        # Message passing layers with residual connections & layer normalization
        for i in range(self.num_layers):
            h_new = self.convs[i](h_dict, edge_index_dict)
            h_dict = {
                k: self.norms[i][k](F.relu(h_new[k]) + h_dict[k])
                for k in h_dict.keys()
            }
            if self.dropout > 0:
                h_dict = {
                    k: F.dropout(v, p=self.dropout, training=self.training)
                    for k, v in h_dict.items()
                }

        # Predict logit for each cell
        logits = self.classifier(h_dict['cell'])
        return logits

    @torch.no_grad()
    def predict_proba(
        self,
        x_dict: Dict[str, torch.Tensor],
        edge_index_dict: Dict[Tuple[str, str, str], torch.Tensor],
    ) -> torch.Tensor:
        """Return sigmoid probabilities for cell nodes [num_cells]."""
        self.eval()
        logits = self.forward(x_dict, edge_index_dict)
        probs = torch.sigmoid(logits).squeeze(-1)
        return probs

