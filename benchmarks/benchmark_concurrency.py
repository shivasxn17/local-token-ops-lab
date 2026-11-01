import asyncio
import time
import json
import aiohttp
import statistics

# Configuration targeting your local vLLM OpenAI-compatible endpoint
API_URL = "http://localhost:8000/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen2.5-Coder-7B-Instruct"

PROMPT = "Write a comprehensive Python script that implements a thread-safe LRU Cache with capacity management."

async def measure_single_request(session, req_id):
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 150,
        "temperature": 0.2,
        "stream": True  # Streaming required to measure TTFT
    }

    start_time = time.perf_counter()
    first_token_time = None
    token_count = 0

    try:
        async with session.post(API_URL, json=payload) as response:
            if response.status != 200:
                print(f"Request {req_id} failed with status {response.status}")
                return None

            async for line in response.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data: ") and line != "data: [DONE]":
                    token_count += 1
                    if first_token_time is None:
                        first_token_time = time.perf_counter()

        end_time = time.perf_counter()
        if first_token_time is None:
            return None

        ttft = (first_token_time - start_time) * 1000  # ms
        total_time = end_time - start_time             # sec
        decode_time = end_time - first_token_time      # sec
        tps = (token_count - 1) / decode_time if decode_time > 0 else 0

        return {
            "req_id": req_id,
            "ttft_ms": ttft,
            "total_time_s": total_time,
            "tokens_generated": token_count,
            "tps": tps
        }
    except Exception as e:
        print(f"Request {req_id} exception: {e}")
        return None

async def run_benchmark(concurrency=2):
    print(f"Starting Token-Ops Benchmark: {concurrency} Concurrent Requests...")
    async with aiohttp.ClientSession() as session:
        tasks = [measure_single_request(session, i) for i in range(concurrency)]
        results = await asyncio.gather(*tasks)

    valid_results = [r for r in results if r is not None]
    if not valid_results:
        print("All benchmark requests failed. Ensure vLLM server is running.")
        return

    ttfts = [r["ttft_ms"] for r in valid_results]
    tpss = [r["tps"] for r in valid_results]

    print("\n" + "="*40)
    print(f"RESULTS (Concurrency Level: {concurrency})")
    print("="*40)
    print(f"Avg TTFT:             {statistics.mean(ttfts):.2f} ms")
    print(f"Avg Decode Speed:     {statistics.mean(tpss):.2f} tokens/sec")
    print(f"Aggregate System TPS: {sum(tpss):.2f} tokens/sec")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(run_benchmark(concurrency=2))
