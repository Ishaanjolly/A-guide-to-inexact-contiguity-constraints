#!/bin/bash
# Download and extract Census Block Assignment Files (BAFs) for feasibility analysis.
#
# Usage:
#     bash scripts/download_baf.sh
#
# Downloads:
#   - 118th Congressional District BAFs
#   - 2022 State Senate (SLDU) BAFs
#   - 2022 State House (SLDL) BAFs
#
# Files are stored in data/baf/{cd118,sldu_2022,sldl_2022}/

set -euo pipefail # Exit on error, undefined variable, or failed pipe

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
BAF_DIR="$ROOT_DIR/data/baf"
TMP_DIR="$BAF_DIR/tmp"

mkdir -p "$BAF_DIR" "$TMP_DIR"

echo "=== Downloading Block Assignment Files ==="
echo ""

# --- Congressional Districts (CD118) ---
echo "[1/3] Downloading 118th Congressional District BAFs..."
curl -L -o "$TMP_DIR/cd118.zip" \
    "https://www2.census.gov/programs-surveys/decennial/rdo/mapping-files/2023/118-congressional-district-bef/cd118.zip"
echo "  Extracting to $BAF_DIR/cd118/"
mkdir -p "$BAF_DIR/cd118"
unzip -o -q "$TMP_DIR/cd118.zip" -d "$BAF_DIR/cd118"
echo "  Done."
echo ""

# --- State Senate (SLDU 2022) ---
echo "[2/3] Downloading 2022 State Senate (SLDU) BAFs..."
curl -L -o "$TMP_DIR/sldu_2022.zip" \
    "https://www2.census.gov/programs-surveys/decennial/rdo/mapping-files/2023/2022-state-legislative-bef/sldu_2022.zip"
echo "  Extracting to $BAF_DIR/sldu_2022/"
mkdir -p "$BAF_DIR/sldu_2022"
unzip -o -q "$TMP_DIR/sldu_2022.zip" -d "$BAF_DIR/sldu_2022"
echo "  Done."
echo ""

# --- State House (SLDL 2022) ---
echo "[3/3] Downloading 2022 State House (SLDL) BAFs..."
curl -L -o "$TMP_DIR/sldl_2022.zip" \
    "https://www2.census.gov/programs-surveys/decennial/rdo/mapping-files/2023/2022-state-legislative-bef/sldl_2022.zip"
echo "  Extracting to $BAF_DIR/sldl_2022/"
mkdir -p "$BAF_DIR/sldl_2022"
unzip -o -q "$TMP_DIR/sldl_2022.zip" -d "$BAF_DIR/sldl_2022"
echo "  Done."
echo ""

# Clean up temp files
rm -rf "$TMP_DIR"

echo "=== All BAF files downloaded and extracted ==="
echo ""
echo "Directory structure:"
echo "  data/baf/cd118/       - Congressional district assignments"
echo "  data/baf/sldu_2022/   - State Senate district assignments"
echo "  data/baf/sldl_2022/   - State House district assignments"
echo ""