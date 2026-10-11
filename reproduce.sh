#!/usr/bin/env bash
# Rebuild every result from the organiser spreadsheets:
#   01 cleaning -> 02 domain analysis -> 03 model comparison, audit, checks and demo/index.html.
# Executed notebook copies are written to reports/executed/ so the committed notebooks stay untouched.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-.venv/bin/python}"
DATA="dataset/01a - DCT Dataset"

for f in flight_data.xlsx "data international_train.xlsx" "data international_test.xlsx" \
         "data domestic_train.xlsx" "data domestic_test.xlsx" Data_Dictionary.pdf; do
  [[ -f "$DATA/$f" ]] || { echo "Missing '$DATA/$f'. Copy the DCT data pack there first (see README)." >&2; exit 1; }
done
command -v node >/dev/null || { echo "Node.js is required for the browser parity checks." >&2; exit 1; }

# Single-threaded BLAS keeps the fitted numbers bit-for-bit reproducible.
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1

mkdir -p reports/executed
for nb in 01_cleaning_features 02_domain_analysis 03_interpretable_models; do
  echo "==> Running $nb"
  "$PYTHON" -m jupyter nbconvert --to notebook --execute \
    --ExecutePreprocessor.kernel_name=python3 --ExecutePreprocessor.timeout=900 \
    --output-dir reports/executed "experiments/notebooks/$nb.ipynb"
done

echo
echo "Done. Open demo/index.html in a browser. Model scores: reports/models/selection_scores.csv"
