from dataclasses import dataclass


@dataclass
class BaseParams:
    """
    Basic parameters for processing
    """

    state_epsg_mapping = {
        "AL": {"name": "Alabama", "epsg": "6355", "congressional_districts": 7},
        "AK": {
            "name": "Alaska",
            "epsg": "6397",
            "congressional_districts": 1,
        },  # Biggest state in the US
        "AZ": {"name": "Arizona", "epsg": "6404", "congressional_districts": 9},
        "AR": {"name": "Arkansas", "epsg": "6410", "congressional_districts": 4},
        "CA": {"name": "California", "epsg": "6419", "congressional_districts": 52},
        "CO": {"name": "Colorado", "epsg": "6427", "congressional_districts": 8},
        "CT": {"name": "Connecticut", "epsg": "6433", "congressional_districts": 5},
        "DE": {"name": "Delaware", "epsg": "6435", "congressional_districts": 1},
        "FL": {"name": "Florida", "epsg": "6440", "congressional_districts": 28},
        "GA": {"name": "Georgia", "epsg": "6444", "congressional_districts": 14},
        "HI": {"name": "Hawaii", "epsg": "6630", "congressional_districts": 2},
        "ID": {"name": "Idaho", "epsg": "6450", "congressional_districts": 2},
        "IL": {"name": "Illinois", "epsg": "6454", "congressional_districts": 17},
        "IN": {"name": "Indiana", "epsg": "6458", "congressional_districts": 9},
        "IA": {"name": "Iowa", "epsg": "6462", "congressional_districts": 4},
        "KS": {"name": "Kansas", "epsg": "6466", "congressional_districts": 4},
        "KY": {"name": "Kentucky", "epsg": "6470", "congressional_districts": 6},
        "LA": {"name": "Louisiana", "epsg": "6476", "congressional_districts": 6},
        "ME": {"name": "Maine", "epsg": "6483", "congressional_districts": 2},
        "MD": {"name": "Maryland", "epsg": "6487", "congressional_districts": 8},
        "MA": {"name": "Massachusetts", "epsg": "6491", "congressional_districts": 9},
        "MI": {"name": "Michigan", "epsg": "6493", "congressional_districts": 13},
        "MN": {"name": "Minnesota", "epsg": "6500", "congressional_districts": 8},
        "MS": {"name": "Mississippi", "epsg": "6506", "congressional_districts": 4},
        "MO": {"name": "Missouri", "epsg": "6512", "congressional_districts": 8},
        "MT": {"name": "Montana", "epsg": "6514", "congressional_districts": 2},
        "NE": {"name": "Nebraska", "epsg": "6516", "congressional_districts": 3},
        "NV": {"name": "Nevada", "epsg": "6518", "congressional_districts": 4},
        "NH": {"name": "New Hampshire", "epsg": "6524", "congressional_districts": 2},
        "NJ": {"name": "New Jersey", "epsg": "6526", "congressional_districts": 12},
        "NM": {"name": "New Mexico", "epsg": "6528", "congressional_districts": 3},
        "NY": {"name": "New York", "epsg": "6534", "congressional_districts": 26},
        "NC": {"name": "North Carolina", "epsg": "6542", "congressional_districts": 14},
        "ND": {"name": "North Dakota", "epsg": "6544", "congressional_districts": 1},
        "OH": {"name": "Ohio", "epsg": "6548", "congressional_districts": 15},
        "OK": {"name": "Oklahoma", "epsg": "6552", "congressional_districts": 5},
        "OR": {"name": "Oregon", "epsg": "6558", "congressional_districts": 6},
        "PA": {"name": "Pennsylvania", "epsg": "6562", "congressional_districts": 17},
        "RI": {"name": "Rhode Island", "epsg": "6567", "congressional_districts": 2},
        "SC": {"name": "South Carolina", "epsg": "6569", "congressional_districts": 7},
        "SD": {"name": "South Dakota", "epsg": "6571", "congressional_districts": 1},
        "TN": {"name": "Tennessee", "epsg": "6575", "congressional_districts": 9},
        "TX": {
            "name": "Texas",
            "epsg": "6583",
            "congressional_districts": 38,
        },  # Second biggest state in the US
        "UT": {"name": "Utah", "epsg": "6619", "congressional_districts": 4},
        "VT": {"name": "Vermont", "epsg": "6589", "congressional_districts": 1},
        "VA": {"name": "Virginia", "epsg": "6592", "congressional_districts": 11},
        "WA": {"name": "Washington", "epsg": "6596", "congressional_districts": 10},
        "WV": {"name": "West Virginia", "epsg": "6600", "congressional_districts": 2},
        "WI": {"name": "Wisconsin", "epsg": "6879", "congressional_districts": 8},
        "WY": {"name": "Wyoming", "epsg": "6613", "congressional_districts": 1},
    }
