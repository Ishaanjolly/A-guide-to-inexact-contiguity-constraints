import json
import os
import struct
from networkx.readwrite import json_graph
from pyproj import Proj
from src.params import BaseParams


def _read_coords_from_dbf(dbf_path):
    """
    Written by Claude
    Read GEOID20 → (INTPTLAT20, INTPTLON20) from a shapefile DBF.

    Returns an empty dict if the file is missing or lacks the required fields.
    """
    if not os.path.exists(dbf_path):
        return {}
    coords = {}
    try:
        with open(dbf_path, "rb") as f:
            # --- parse header ---
            header = f.read(32)
            num_records = struct.unpack_from("<I", header, 4)[0]
            header_size = struct.unpack_from("<H", header, 8)[0]
            record_size = struct.unpack_from("<H", header, 10)[0]

            # --- parse field descriptors ---
            fields = []
            while True:
                desc = f.read(32)
                if desc[0] == 13:  # field terminator
                    break
                name = desc[:11].replace(b"\x00", b"").decode("ascii")
                length = desc[16]
                fields.append((name, length))

            # find column offsets
            col_offset = {}
            offset = 1  # leading deletion flag byte
            for name, length in fields:
                col_offset[name] = (offset, length)
                offset += length

            needed = {"GEOID20", "INTPTLAT20", "INTPTLON20"}
            if not needed.issubset({f[0] for f in fields}):
                return {}

            # seek to start of records
            f.seek(header_size)
            for _ in range(num_records):
                raw = f.read(record_size)
                geoid = (
                    raw[
                        col_offset["GEOID20"][0] : col_offset["GEOID20"][0]
                        + col_offset["GEOID20"][1]
                    ]
                    .decode("ascii")
                    .strip()
                )
                lat = (
                    raw[
                        col_offset["INTPTLAT20"][0] : col_offset["INTPTLAT20"][0]
                        + col_offset["INTPTLAT20"][1]
                    ]
                    .decode("ascii")
                    .strip()
                )
                lon = (
                    raw[
                        col_offset["INTPTLON20"][0] : col_offset["INTPTLON20"][0]
                        + col_offset["INTPTLON20"][1]
                    ]
                    .decode("ascii")
                    .strip()
                )
                coords[geoid] = (float(lat), float(lon))
    except Exception:
        return {}
    return coords


def read_graph_from_json(
    json_file, state=None, update_population=True, rescale_distance=True
):
    """
    Reads a graph from a JSON adjacency file and optionally enriches node attributes.

    Args:
        json_file (str): Path to the JSON file in NetworkX adjacency format.
        state (str or None): Two-letter state abbreviation (e.g. ``'IA'``).
            When provided, sets ``C_X``/``C_Y`` (geographic centroid in
            degrees), ``X``/``Y`` (projected centroid in km), and ``TOTPOP``
            on every node. When ``None``, projection is skipped.
        update_population (bool): If ``True``, sets ``TOTPOP = P0010001`` on
            every node. Ignored when ``state`` is provided. Defaults to
            ``True``.
        rescale_distance (bool): If ``True``, divides ``area``,
            ``boundary_perim``, and ``shared_perim`` by 100,000 to convert
            metres to ~100 km units for better Gurobi conditioning. Defaults
            to ``True``.

    Returns:
        networkx.Graph: The loaded graph with enriched node attributes.
    """
    with open(json_file) as f:
        data = json.load(f)

    G = json_graph.adjacency_graph(data)

    if state is not None:
        epsg = BaseParams().state_epsg_mapping[state]["epsg"]
        proj = Proj(f"EPSG:{epsg}", preserve_units=True)
        sample = G.nodes[next(iter(G.nodes))]
        lon_key = (
            "INTPTLON20"
            if "INTPTLON20" in sample
            else "INTPTLON"
            if "INTPTLON" in sample
            else None
        )
        lat_key = (
            "INTPTLAT20"
            if "INTPTLAT20" in sample
            else "INTPTLAT"
            if "INTPTLAT" in sample
            else None
        )

        if lon_key and lat_key:
            # Coordinates already in the JSON
            for i in G.nodes:
                G.nodes[i]["C_X"] = float(G.nodes[i][lon_key])
                G.nodes[i]["C_Y"] = float(G.nodes[i][lat_key])
                x_m, y_m = proj(G.nodes[i]["C_X"], G.nodes[i]["C_Y"])
                G.nodes[i]["X"] = x_m / 1000  # meters to km
                G.nodes[i]["Y"] = y_m / 1000
        else:
            # Fallback: read INTPTLAT20/INTPTLON20 from the companion .dbf file - thanks Claude
            dbf_path = os.path.splitext(json_file)[0] + ".dbf"
            dbf_coords = _read_coords_from_dbf(dbf_path)
            if dbf_coords:
                for i in G.nodes:
                    geoid = G.nodes[i].get("GEOID20", "")
                    if geoid in dbf_coords:
                        lat, lon = dbf_coords[geoid]
                        G.nodes[i]["C_X"] = lon
                        G.nodes[i]["C_Y"] = lat
                        x_m, y_m = proj(lon, lat)
                        G.nodes[i]["X"] = x_m / 1000
                        G.nodes[i]["Y"] = y_m / 1000

    if update_population:
        for i in G.nodes:
            G.nodes[i]["TOTPOP"] = int(G.nodes[i]["P0010001"])

    if rescale_distance:
        ht = 100000
        for i in G.nodes:
            if "area" in G.nodes[i]:
                G.nodes[i]["area"] /= ht * ht
            if G.nodes[i].get("boundary_node") and "boundary_perim" in G.nodes[i]:
                G.nodes[i]["boundary_perim"] /= ht
        for i, j in G.edges:
            if "shared_perim" in G.edges[i, j]:
                G.edges[i, j]["shared_perim"] /= ht

    return G
