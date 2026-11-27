#!/bin/sh
# Clone the committed HEAD into a temporary directory, check the pinned inputs, regenerate the SI fragments, the docs fragments,
# their estimate side files and Fig. 2 there, and compare them with the committed outputs. Uncommitted changes are not tested.
# Fig. 2 is compared byte for byte, which assumes the matplotlib of requirements.txt.
set -eu
REPO=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
git clone -q "$REPO" "$T/repo"
cd "$T/repo"
shasum -a 256 -c --quiet data/inputs-sha256.txt
python3 si_tables.py "$T/si" "$T/docs" "$T/counts.json" > /dev/null
python3 attention.py "$T/si" "$T/attention.json" > /dev/null
python3 fig_census_fieldmap.py data/fields "$T/fig" > /dev/null
diff -r si "$T/si"
diff -r docs/fragments "$T/docs"
cmp data/estimates-counts-policy2.json "$T/counts.json"
cmp data/estimates-attention-policy2.json "$T/attention.json"
cmp fig/census-fieldmap.pdf "$T/fig.pdf"
cmp fig/census-fieldmap.png "$T/fig.png"
test -z "$(git status --porcelain)"
echo "clean clone OK: $(ls si | wc -l | tr -d ' ') SI fragments, $(ls docs/fragments | wc -l | tr -d ' ') docs fragments and Fig. 2 regenerate identically"
