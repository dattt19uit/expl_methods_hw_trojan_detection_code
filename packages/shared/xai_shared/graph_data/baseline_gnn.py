"""
Homogeneous Graph Neural Network for Baseline NetlistX Circuit Graphs.

Symmetric counterpart to HeteroTrojanGNN:
- Same 2-layer GraphSAGE architecture
- Same hidden_dim (64)
- Same LayerNorm and residual connections
- Same dropout (0.2)
- Same 2-layer MLP classifier head
"""

from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv, Linear


class BaselineTrojanGNN(nn.Module):
    """
    Homogeneous GNN for baseline circuit graph node binary classification (Trojan vs Benign).
    Operates on author's NetlistX graph representation.
    """

    def __init__(
        self,
        in_channels: int = 13,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.in_channels = in_channels
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout = dropout

        # Input feature projection
        self.node_in = Linear(in_channels, hidden_dim)

        # Message passing layers with LayerNorm
        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()
        for _ in range(num_layers):
            self.convs.append(SAGEConv(hidden_dim, hidden_dim))
            self.norms.append(nn.LayerNorm(hidden_dim))

        # Classifier head (identical to HeteroTrojanGNN)
        self.classifier = nn.Sequential(
            Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            Linear(hidden_dim // 2, 1),
        )

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        Forward pass returning unnormalized logits for all graph nodes.
        Shape: [num_nodes, 1]
        """
        h = F.relu(self.node_in(x))

        for i in range(self.num_layers):
            h_new = self.convs[i](h, edge_index)
            # Residual connection + LayerNorm
            h = self.norms[i](F.relu(h_new) + h)
            if self.dropout > 0:
                h = F.dropout(h, p=self.dropout, training=self.training)

        logits = self.classifier(h)
        return logits
