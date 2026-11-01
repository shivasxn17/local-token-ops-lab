# Launching the vLLM Server

To launch the vLLM server directly from your terminal, use the modern `vllm serve` command:

```bash
vllm serve Qwen/Qwen2.5-Coder-7B-Instruct-AWQ \
  --quantization awq \
  --gpu-memory-utilization 0.75 \
  --enforce-eager \
  --max-model-len 2048 \
  --dtype float16 \
  --host 0.0.0.0 \
  --port 8000
```

### Why this command works:

* **`vllm serve`**: The recommended entrypoint in modern vLLM versions (replacing the older `python3 -m vllm.entrypoints.openai.api_server` module path).
* **`Qwen2.5-Coder-7B-Instruct-AWQ`**: Uses a 4-bit AWQ quantized variant. Unquantized 7B models require ~14GB VRAM, whereas this 4-bit version takes ~4.5GB VRAM—fitting inside your GTX 1660 Super's 6GB limit.
* **`--gpu-memory-utilization 0.75`**: Requests 0.75 × 6.0 GiB = 4.5 GiB, which easily fits within your 5.01 GiB available limit.
* **`--enforce-eager`**: Disables CUDA Graph capture memory overhead, saving ~300-500MB of VRAM during initialization.
* **`--max-model-len 2048`**: Limits the maximum context window to manage KV cache memory footprint.

Once the server finishes loading and displays `Application startup complete`, open a second WSL terminal window, activate your `venv`, and run the fixed benchmark script:

```bash
source ~/local-token-ops-lab/venv/bin/activate
pip install aiohttp
python3 ~/local-token-ops-lab/benchmarks/benchmark_concurrency.py
```