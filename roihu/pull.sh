#!/bin/bash
# Download the pinned model snapshot into the work dir hf-home on a cluster login node (download only, no inference),
# write refs/main if the pinned download left none (known trap), and record weight sha256 in W/logs/weights-sha256-<model>.txt.
#   bash pull.sh [REPO] [REVISION]
# Site settings as in xfam.sbatch: XFAM_WORK (required), XFAM_ENV_SCRIPT and XFAM_MODULE (optional).
set -euo pipefail
REPO=${1:-google/gemma-4-31B-it-qat-w4a16-ct}; REV=${2:-52f3f65bc7a02d555763bc923bd1d9094898219d}
W="${XFAM_WORK:?set XFAM_WORK to the work dir}"
if [ -n "${XFAM_ENV_SCRIPT:-}" ]; then set +u +e; source "$XFAM_ENV_SCRIPT"; set -u -e; fi
if [ -n "${XFAM_MODULE:-}" ]; then module load "$XFAM_MODULE"; fi
export HF_HOME=$W/hf-home HF_TOKEN_PATH=$HOME/.cache/huggingface/token
mkdir -p "$HF_HOME" "$W/logs"
SNAP=$(python3 - "$REPO" "$REV" <<'EOF'
import sys
from pathlib import Path
from huggingface_hub import snapshot_download
repo, rev = sys.argv[1:]
p = Path(snapshot_download(repo, revision=rev))
refs = p.parents[1] / "refs" / "main"
if not refs.exists():
    refs.parent.mkdir(parents=True, exist_ok=True)
    refs.write_text(p.name)
    print("wrote refs/main", file=sys.stderr)
print(p)
EOF
)
echo "SNAPSHOT $SNAP"
{ echo "# $REPO @ $REV ($(date -Is))"; cd "$SNAP" && find -L . -type f | sort | xargs sha256sum; } > "$W/logs/weights-sha256-${REPO##*/}.txt"
du -shL "$SNAP"
