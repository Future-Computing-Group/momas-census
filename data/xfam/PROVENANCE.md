# Open-weight coding runs: provenance

Each run served one model with vLLM on one GPU and coded the calls file with `roihu/xfam_client.py` (`roihu/xfam.sbatch`). Common to all runs: vLLM 0.19.1; GPU class NVIDIA GH200 120GB (97,871 MiB, driver 615.71.09), one GPU per run; `vllm serve` with `--max-model-len 8192 --gpu-memory-utilization 0.92 --enable-prefix-caching --seed 0 --generation-config vllm`; client `--max-tokens 1024`. Parsed codes are in `<run>/results-parsed.jsonl` and parse failures in `<run>/failures.jsonl`.

Models (Hugging Face repository at the pinned snapshot revision; per-file weight sha256 in `smoke/weights-sha256.txt` and `smoke5-qwen72/weights-sha256.txt`):

- `gemma-4-31b-qat`: `google/gemma-4-31B-it-qat-w4a16-ct` at revision `52f3f65bc7a02d555763bc923bd1d9094898219d`.
- `qwen2.5-72b-awq`: `Qwen/Qwen2.5-72B-Instruct-AWQ` at revision `698703eae6604af048a3d2f509995dc302088217`.

| run | model | calls file | calls sha256 | client sha256 | codebook-v3.md sha256 | workers | parsed / failed |
|---|---|---|---|---|---|---|---|
| smoke | gemma-4-31b-qat | calls-smoke100.jsonl | be7a442fc7aafd080839808bef633ac88cbfa2b9a49aec1cb107892c289952be | b01d2aaae3aab0f0e16c0cccce7c407209dee38c789d5c412f90ffbf92ab9c08 | (not recorded) | 16 | 100 / 0 |
| smoke2 | gemma-4-31b-qat | calls-smoke2.jsonl | bdc7898149a38104ddbeae47e444a6eec3ae1701deaedf17c8b0f6e905918a24 | b01d2aaae3aab0f0e16c0cccce7c407209dee38c789d5c412f90ffbf92ab9c08 | 74a524ee67c59111e3cea0da888f2b8450ee395a37f2b09682fcdb4927ca7823 | 16 | 100 / 0 |
| smoke3 | gemma-4-31b-qat | calls-smoke3.jsonl | 2fb912472ac8d9934c2b0549507ddc02022bad26d9f5a4be3da003df9f82d132 | b01d2aaae3aab0f0e16c0cccce7c407209dee38c789d5c412f90ffbf92ab9c08 | 6dec1cb12e0a59f9703e0c0b742282ff14f905ef9a2062de63f69f44cc980605 | 16 | 100 / 0 |
| smoke4 | gemma-4-31b-qat | calls-smoke4.jsonl | 07dcfc20d82702049e314221253366e567510ab0152507de2df446c7a0064144 | b01d2aaae3aab0f0e16c0cccce7c407209dee38c789d5c412f90ffbf92ab9c08 | cfbf4831b695c37537c4a19af21fb8ddae6794295f49b576753aeeb77d6bfb72 | 16 | 100 / 0 |
| smoke5-gemma | gemma-4-31b-qat | calls-smoke5.jsonl | 9e3edb6b18e62bd0aa9da03acf9572f85d5c716d4c6b4252db75fff617d739a6 | 40838153ac4f19a9687415897a96c0f10ef42974a92d94babb4d6029118e541f | codebook-v3.md (v3.4) | 16 | 100 / 0 |
| smoke5-qwen72 | qwen2.5-72b-awq | calls-smoke5.jsonl | 9e3edb6b18e62bd0aa9da03acf9572f85d5c716d4c6b4252db75fff617d739a6 | 40838153ac4f19a9687415897a96c0f10ef42974a92d94babb4d6029118e541f | codebook-v3.md (v3.4) | 16 | 100 / 0 |
| full-v34 | gemma-4-31b-qat | calls.jsonl | f103385b3f8792bb73a0061d6667da5f0cd95dc5c68bbd5878b9336969fd48e3 | 40838153ac4f19a9687415897a96c0f10ef42974a92d94babb4d6029118e541f | codebook-v3.md (v3.4) | 64 | 12,383 / 0 |
| ext-v34 | gemma-4-31b-qat | calls-ext.jsonl | f4c86a799764dd7cd589ddae5e9acd179bd6b1b0883be951447d81904ae925fc | 40838153ac4f19a9687415897a96c0f10ef42974a92d94babb4d6029118e541f | codebook-v3.md (v3.4) | 64 | 3,968 / 0 |
| ext-ea-v34 | gemma-4-31b-qat | calls-ext-ea.jsonl | 3e802a1601e7b1f5b0c0c930c0c35e5549eb5d19438711b9068d25813245d913 | 40838153ac4f19a9687415897a96c0f10ef42974a92d94babb4d6029118e541f | codebook-v3.md (v3.4) | 64 | 160 / 0 |
| policy-smoke | gemma-4-31b-qat | calls-policy-smoke100.jsonl | 6296d62dec74e3625ae49e253b639ab2047be56a014b28bad6854f66cef17045 | 40838153ac4f19a9687415897a96c0f10ef42974a92d94babb4d6029118e541f | codebook-v3.md (v3.4) | 64 | 100 / 0 |
| policy-smoke2 | gemma-4-31b-qat | calls-policy-smoke2.jsonl | d3230ad4ee51841c952bd0e9b35289f1dabba7975fdf34f97977e56acc4c2b75 | 40838153ac4f19a9687415897a96c0f10ef42974a92d94babb4d6029118e541f | codebook-v3.md (v3.4) | 64 | 100 / 0 |
| policy-v1 | gemma-4-31b-qat | calls-policy.jsonl | aac8eacf04d26ae73a2aed7838b962cf0eceb315a5efb9ba2a36223c605550ed | 40838153ac4f19a9687415897a96c0f10ef42974a92d94babb4d6029118e541f | codebook-v3.md (v3.4) | 64 | 16,507 / 4 |

The client hash `40838153...` is that of the tracked `roihu/xfam_client.py`; the codebook column names the tracked `codebook-v3.md` (v3.4). The calls files of the extension runs are also listed with their items files in `ext-sha256.txt`.

The policy runs carry codebook-policy.md v1 (sha256 f89a80bfed6c81fe5c178e46efc8170c6a095444d68d1b4d525c593850d01953) as the system prompt inside their calls files; the codebook-v3.md column is the file the job script hashes, unchanged. Their calls files are listed with the items files in `policy-sha256.txt`. The 4 policy-v1 failures are degenerate generations (a quote filled with repeated no-break spaces until max_tokens, finish_reason length); deterministic decoding repeats them, so they were not re-run and the confirmer codes those papers in full.
