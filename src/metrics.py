import math


def polsby_popper(G, district, label):
    area = sum(G.nodes[i]["area"] for i in district)
    perim = sum(
        G.edges[u, v]["shared_perim"]
        for u in district
        for v in G.neighbors(u)
        if label[u] != label[v]
    )
    perim += sum(
        G.nodes[i]["boundary_perim"] for i in district if G.nodes[i]["boundary_node"]
    )
    return 4 * math.pi * area / (perim * perim)


def create_label_mapping(districts):
    label = {i: j for j in range(len(districts)) for i in districts[j]}
    return label


def average_polsby_popper(G, districts, verbose=False):
    label = create_label_mapping(districts)
    if verbose:
        print("\nDistrict Polsby-Popper scores:")
        for p in range(len(districts)):
            print(p, round(polsby_popper(G, districts[p], label), 4))
    return sum(polsby_popper(G, district, label) for district in districts) / len(
        districts
    )


def bottleneck_polsby_popper(G, districts, verbose=False):
    label = create_label_mapping(districts)
    if verbose:
        print("\nDistrict Polsby-Popper scores:")
        for p in range(len(districts)):
            print(p, round(polsby_popper(G, districts[p], label), 4))
    return min(polsby_popper(G, district, label) for district in districts)


def cut_edges(G, districts):
    label = create_label_mapping(districts)
    return sum(1 for i, j in G.edges if label[i] != label[j])


def total_deviation(G, districts, verbose=False):
    populations = [
        sum(G.nodes[i]["TOTPOP"] for i in district) for district in districts
    ]
    if verbose:
        print("\nDistrict populations:")
        for p in range(len(districts)):
            print(p, populations[p])
    return max(populations) - min(populations)
