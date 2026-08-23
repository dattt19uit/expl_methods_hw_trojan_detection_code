import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt


FOLDER_PATH = "data/circuits/graphs/RS232-T1000_90nm/"
NODES_FILE = FOLDER_PATH + "nodes.csv"
EDGES_FILE = FOLDER_PATH + "edges.csv"

# Set to None to visualize the entire graph.
TARGET_NODE = None

# Number of edges to traverse from TARGET_NODE in both directions.
HOPS = 2

OUTPUT_IMAGE = "graph.png"


def load_graph(nodes_file, edges_file):
    nodes_df = pd.read_csv(nodes_file)
    edges_df = pd.read_csv(edges_file)

    print(f"Loaded nodes : {len(nodes_df)}")
    print(f"Loaded edges : {len(edges_df)}")

    G = nx.DiGraph()

    # Load nodes and preserve their attributes.
    for _, row in nodes_df.iterrows():
        node = row["node"]
        G.add_node(node, output=row.get("output", False), type=row.get("type", ""))

    # Load directed edges.
    for _, row in edges_df.iterrows():
        source = row["source"]
        target = row["target"]

        # Add missing nodes referenced by edges.
        if source not in G:
            G.add_node(source)

        if target not in G:
            G.add_node(target)

        G.add_edge(source, target)

    return G


def get_subgraph(G, target_node, hops=2):
    if target_node not in G:
        raise ValueError(f"Node '{target_node}' does not exist in the graph.")

    nodes = {target_node}
    current = {target_node}

    # Traverse both predecessors and successors for each hop.
    for _ in range(hops):
        next_nodes = set()

        for node in current:
            next_nodes.update(G.predecessors(node))
            next_nodes.update(G.successors(node))

        nodes.update(next_nodes)
        current = next_nodes

    return G.subgraph(nodes).copy()


def get_node_color(node_data):
    node_type = node_data.get("type", "")

    if node_data.get("output") is True:
        return "red"

    if node_type == "bb_input":
        return "green"

    if node_type == "bb_output":
        return "orange"

    if node_type:
        return "skyblue"

    return "gray"


def visualize_graph(G, output_file):
    print()
    print("Graph information")
    print("------------------")
    print(f"Nodes      : {G.number_of_nodes()}")
    print(f"Edges      : {G.number_of_edges()}")
    print(f"Components : {nx.number_weakly_connected_components(G)}")

    print("Calculating layout...")

    pos = nx.spring_layout(G, seed=42, k=1.5, iterations=100)

    plt.figure(figsize=(24, 18))

    node_colors = [get_node_color(G.nodes[node]) for node in G.nodes]

    nx.draw_networkx_edges(
        G,
        pos,
        arrows=True,
        arrowsize=10,
        alpha=0.3,
        edge_color="gray"
    )

    nx.draw_networkx_nodes(
        G,
        pos,
        node_size=80,
        node_color=node_colors,
        alpha=0.9
    )

    # Labels are useful for small subgraphs but make large graphs unreadable.
    if G.number_of_nodes() <= 150:
        nx.draw_networkx_labels(G, pos, font_size=7)

    plt.title(
        f"Verilog Circuit Graph\n"
        f"{G.number_of_nodes()} nodes / {G.number_of_edges()} edges"
    )

    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_file, dpi=200, bbox_inches="tight")
    plt.show()

    print()
    print(f"Saved: {output_file}")


def main():
    G = load_graph(NODES_FILE, EDGES_FILE)

    if TARGET_NODE is None:
        visualize_graph(G, OUTPUT_IMAGE)
        return

    print(f"\nVisualizing {HOPS}-hop neighborhood around '{TARGET_NODE}'")

    subgraph = get_subgraph(G, TARGET_NODE, HOPS)
    visualize_graph(subgraph, OUTPUT_IMAGE)


if __name__ == "__main__":
    main()