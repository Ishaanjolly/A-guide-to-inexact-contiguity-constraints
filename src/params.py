from dataclasses import dataclass


@dataclass
class BaseParams:
    """
    Basic parameters for processing
    """

    state_epsg_mapping = {
        "AL": {"name": "Alabama", "epsg": "6355"},
        "AK": {"name": "Alaska","epsg": "6397"}, 
        "AZ": {"name": "Arizona", "epsg": "6404"},
        "AR": {"name": "Arkansas", "epsg": "6410"},
        "CA": {"name": "California", "epsg": "6419"},
        "CO": {"name": "Colorado", "epsg": "6427"},
        "CT": {"name": "Connecticut", "epsg": "6433"},
        "DE": {"name": "Delaware", "epsg": "6435"},
        "FL": {"name": "Florida", "epsg": "6440"},
        "GA": {"name": "Georgia", "epsg": "6444"},
        "HI": {"name": "Hawaii", "epsg": "6630"},
        "ID": {"name": "Idaho", "epsg": "6450"},
        "IL": {"name": "Illinois", "epsg": "6454"},
        "IN": {"name": "Indiana", "epsg": "6458"},
        "IA": {"name": "Iowa", "epsg": "6462"},
        "KS": {"name": "Kansas", "epsg": "6466"},
        "KY": {"name": "Kentucky", "epsg": "6470"},
        "LA": {"name": "Louisiana", "epsg": "6476"},
        "ME": {"name": "Maine", "epsg": "6483"},
        "MD": {"name": "Maryland", "epsg": "6487"},
        "MA": {"name": "Massachusetts", "epsg": "6491"},
        "MI": {"name": "Michigan", "epsg": "6493"},
        "MN": {"name": "Minnesota", "epsg": "6500"},
        "MS": {"name": "Mississippi", "epsg": "6506"},
        "MO": {"name": "Missouri", "epsg": "6512"},
        "MT": {"name": "Montana", "epsg": "6514"},
        "NE": {"name": "Nebraska", "epsg": "6516"},
        "NV": {"name": "Nevada", "epsg": "6518",},
        "NH": {"name": "New Hampshire", "epsg": "6524"},
        "NJ": {"name": "New Jersey", "epsg": "6526"},
        "NM": {"name": "New Mexico", "epsg": "6528"},
        "NY": {"name": "New York", "epsg": "6534"},
        "NC": {"name": "North Carolina", "epsg": "6542"},
        "ND": {"name": "North Dakota", "epsg": "6544"},
        "OH": {"name": "Ohio", "epsg": "6548"},
        "OK": {"name": "Oklahoma", "epsg": "6552"},
        "OR": {"name": "Oregon", "epsg": "6558"},
        "PA": {"name": "Pennsylvania", "epsg": "6562"},
        "RI": {"name": "Rhode Island", "epsg": "6567"},
        "SC": {"name": "South Carolina", "epsg": "6569"},
        "SD": {"name": "South Dakota", "epsg": "6571"},
        "TN": {"name": "Tennessee", "epsg": "6575"},
        "TX": {"name": "Texas","epsg": "6583"}, 
        "UT": {"name": "Utah", "epsg": "6619"},
        "VT": {"name": "Vermont", "epsg": "6589"},
        "VA": {"name": "Virginia", "epsg": "6592"},
        "WA": {"name": "Washington", "epsg": "6596"},
        "WV": {"name": "West Virginia", "epsg": "6600"},
        "WI": {"name": "Wisconsin", "epsg": "6879"},
        "WY": {"name": "Wyoming", "epsg": "6613"},
    }
    state_fips_mapping = {
        "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
        "CO": "08", "CT": "09", "DE": "10", "FL": "12", "GA": "13",
        "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19",
        "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24",
        "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29",
        "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34",
        "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
        "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45",
        "SD": "46", "TN": "47", "TX": "48", "UT": "49", "VT": "50",
        "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56",
        }
    # String because they have leading zeros that matter

    congressional_districts_2020 = {
        "CA": 52, "TX": 38, "FL": 28, "NY": 26, "PA": 17,
        "IL": 17, "OH": 15, "GA": 14, "NC": 14, "MI": 13,
        "NJ": 12, "VA": 11, "WA": 10, "AZ": 9,  "MA": 9,
        "TN": 9,  "IN": 9,  "MD": 8,  "MO": 8,  "WI": 8,
        "CO": 8,  "MN": 8,  "SC": 7,  "AL": 7,  "LA": 6,
        "KY": 6,  "OR": 6,  "OK": 5,  "CT": 5,  "UT": 4,
        "IA": 4,  "NV": 4,  "AR": 4,  "MS": 4,  "KS": 4,
        "NM": 3,  "NE": 3,  "ID": 2,  "WV": 2,  "HI": 2,
        "NH": 2,  "ME": 2,  "RI": 2,  "MT": 2,  "DE": 1,
        "SD": 1,  "ND": 1,  "AK": 1,  "VT": 1,  "WY": 1,
    }

    state_house_districts_2020 = {
        "AL": 105, "AK": 40,  "AZ": 30,  "AR": 100, "CA": 80,
        "CO": 65,  "CT": 151, "DE": 41,  "FL": 120, "GA": 180,
        "HI": 51,  "ID": 35,  "IL": 118, "IN": 100, "IA": 100,
        "KS": 125, "KY": 100, "LA": 105, "ME": 151, "MD": 47,
        "MA": 160, "MI": 110, "MN": 134, "MS": 122, "MO": 163,
        "MT": 100, "NE": 0,   "NV": 42,  "NH": 400, "NJ": 40,
        "NM": 70,  "NY": 150, "NC": 120, "ND": 47,  "OH": 99,
        "OK": 101, "OR": 60,  "PA": 203, "RI": 75,  "SC": 124,
        "SD": 35,  "TN": 99,  "TX": 150, "UT": 75,  "VT": 150,
        "VA": 100, "WA": 49,  "WV": 100, "WI": 99,  "WY": 62,
    }

    state_senate_districts_2020 = {
        "AL": 35, "AK": 20, "AZ": 30, "AR": 35, "CA": 40,
        "CO": 35, "CT": 36, "DE": 21, "FL": 40, "GA": 56,
        "HI": 25, "ID": 35, "IL": 59, "IN": 50, "IA": 50,
        "KS": 40, "KY": 38, "LA": 39, "ME": 35, "MD": 47,
        "MA": 40, "MI": 38, "MN": 67, "MS": 52, "MO": 34,
        "MT": 50, "NE": 49, "NV": 21, "NH": 24, "NJ": 40,
        "NM": 42, "NY": 63, "NC": 50, "ND": 47, "OH": 33,
        "OK": 48, "OR": 30, "PA": 50, "RI": 38, "SC": 46,
        "SD": 35, "TN": 33, "TX": 31, "UT": 29, "VT": 30,
        "VA": 40, "WA": 49, "WV": 17, "WI": 33, "WY": 31,
    }
