import matplotlib.pyplot as plt
import networkx as nx


def print_changes(changes_dict):
    print("\n\n")
    print("changesDict")
    changes_description = ""
    for change in changes_dict:
        if change == 0:
            continue
        table, prev, new = changes_dict[change]
        changes_description += f"{change} {table} \n    Prev: {prev} \n    New: {new}\n"
        print(change, table, prev, new)
    print("\n\n")
    return changes_description


def draw_graph(graph):
    pos = nx.spring_layout(graph, k=1.5)

    for key, value in pos.items():
        pos[key] = (value[0] + 1, value[1])

    labels = {node: f"{node}\nOrd:{graph.nodes[node]['order']}" for node in graph.nodes()}

    nx.draw(
        graph,
        pos,
        labels=labels,
        with_labels=True,
        arrows=True,
        node_size=3000,
        font_size=20,
        node_shape="s",
    )

    plt.xlim(-2, 2)
    plt.ylim(-2, 2)
    plt.show()
