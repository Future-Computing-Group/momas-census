#!/bin/bash
#SBATCH --gres=gpu:gh200:1
#SBATCH --cpus-per-task=16
#SBATCH --no-requeue
#SBATCH --job-name=inttime-xfam
# Open-weight coding of conference abstracts on one GH200: serve the model with vLLM, run xfam_client.py against it, parse.
#
#   sbatch --account="$XFAM_ACCOUNT" --partition=... --time=... --output="$XFAM_WORK/logs/slurm-%j.out" --export=ALL \
#       roihu/xfam.sbatch MODEL_DIR NAME CALLS RUN [WORKERS] [MAXLEN] [MAXTOK]
#
# Site settings come from the environment (no defaults): XFAM_WORK is the work dir holding code/ (xfam_client.py,
# codebook-v3.md) and hf-home/; optional XFAM_ENV_SCRIPT is sourced first (site module init) and XFAM_MODULE is loaded
# with `module load` (e.g. a vLLM 0.19.1 module). CALLS is a calls.jsonl; results go to W/runs/RUN/results
# (resumable: existing results are skipped).
set -euo pipefail
MODEL_DIR="${1:?model snapshot dir}"; NAME="${2:?served model name}"; CALLS="${3:?calls.jsonl}"; RUN="${4:?run name}"
WORKERS="${5:-16}"; MAXLEN="${6:-8192}"; MAXTOK="${7:-1024}"
W="${XFAM_WORK:?set XFAM_WORK to the work dir}"
CLIENT=$W/code/roihu/xfam_client.py

if [ -n "${XFAM_ENV_SCRIPT:-}" ]; then set +u +e; source "$XFAM_ENV_SCRIPT"; set -u -e; fi
if [ -n "${XFAM_MODULE:-}" ]; then module load "$XFAM_MODULE"; fi
export HF_HOME=$W/hf-home HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1
PORT=$((8000 + ${SLURM_JOB_ID:-0} % 1000))
R=$W/runs/$RUN; OUT=$R/job-$SLURM_JOB_ID; mkdir -p "$OUT" "$R/results"

python3 -c "import sys,torch; torch.cuda.is_available() or sys.exit('FATAL: no CUDA, refusing billed work'); print('GPU OK', torch.cuda.get_device_name(0))"
{ echo "model=$MODEL_DIR name=$NAME job=$SLURM_JOB_ID node=$(hostname) date=$(date -Is) workers=$WORKERS maxlen=$MAXLEN maxtok=$MAXTOK calls=$CALLS"
  python3 -c "import vllm; print('vllm', vllm.__version__)"
  sha256sum "$CALLS" "$CLIENT" "$W/code/codebook-v3.md"
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader; } | tee "$OUT/env.txt"

# no --kv-cache-dtype fp8 (fails with 4-bit kernels at engine init)
vllm serve "$MODEL_DIR" --served-model-name "$NAME" --port "$PORT" --max-model-len "$MAXLEN" --gpu-memory-utilization 0.92 \
    --enable-prefix-caching --seed 0 --generation-config vllm > "$OUT/vllm-server.log" 2>&1 &
SRV=$!
trap 'kill "$SRV" 2>/dev/null || true' EXIT
READY=0
for _ in $(seq 1 240); do
  if curl -sf "http://localhost:$PORT/v1/models" 2>/dev/null | grep -qF "$NAME"; then READY=1; break; fi
  kill -0 "$SRV" 2>/dev/null || { echo "FATAL: vLLM exited during load"; tail -40 "$OUT/vllm-server.log"; exit 3; }
  sleep 5
done
[ "$READY" = 1 ] || { echo "FATAL: server not ready in 1200 s"; tail -40 "$OUT/vllm-server.log"; exit 4; }
echo "SERVER READY $(date -Is)"

T0=$(date +%s)
CUDA_VISIBLE_DEVICES= python3 "$CLIENT" run --calls "$CALLS" --results "$R/results" --base-url "http://localhost:$PORT/v1" \
    --model "$NAME" --workers "$WORKERS" --max-tokens "$MAXTOK" > "$OUT/client.log" 2>&1 &
CL=$!
sleep 60; nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv | tee "$OUT/nvidia-smi-1min.txt"
wait "$CL"
echo "CLIENT DONE $(date -Is) elapsed=$(( $(date +%s) - T0 ))s results=$(ls "$R/results" | wc -l) failed=$(grep -c failed "$OUT/client.log" || true)"
CUDA_VISIBLE_DEVICES= python3 "$CLIENT" parse --calls "$CALLS" --results "$R/results" --out "$R/results-parsed.jsonl" --failures "$R/failures.jsonl"
grep -h "throughput" "$OUT/vllm-server.log" | tail -3 || true
