"""
Performance testing script for Rural AI Doctor
Features: Concurrent request simulation and P95 latency tracking.
"""

import asyncio
import time
import statistics
from httpx import AsyncClient, Limits
import json

# Configuration
BASE_URL = "http://localhost:8000"
CONCURRENT_REQUESTS = 5  # Simulating multiple users
TOTAL_REQUESTS = 20

async def test_endpoint(client: AsyncClient, endpoint: str, payload: dict):
    """Test single endpoint with timing."""
    start = time.time()
    try:
        response = await client.post(endpoint, json=payload, timeout=30.0)
        duration = time.time() - start
        return duration, response.status_code
    except Exception as e:
        return time.time() - start, f"Error: {str(e)}"

async def run_batch(client: AsyncClient, endpoint: str, payload_gen, batch_name: str):
    """Runs a batch of requests concurrently and reports stats."""
    print(f"\n🚀 Starting performance test: {batch_name}")
    
    tasks = []

    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

    async def sem_task(i):
        async with semaphore:
            payload = payload_gen(i)
            return await test_endpoint(client, endpoint, payload)

    results = await asyncio.gather(*(sem_task(i) for i in range(TOTAL_REQUESTS)))
    
    durations = [r[0] for r in results]
    statuses = [r[1] for r in results]
    
    # Calculate Statistics
    mean_lat = statistics.mean(durations)
    p95_lat = statistics.quantiles(durations, n=20)[18]  # 95th percentile
    success_rate = (statuses.count(200) / TOTAL_REQUESTS) * 100

    print(f"📊 Results for {batch_name}:")
    print(f"   - Success Rate: {success_rate}%")
    print(f"   - Mean Latency: {mean_lat:.3f}s")
    print(f"   - P95 Latency:  {p95_lat:.3f}s (Critical for rural UX)")
    print(f"   - Min/Max:      {min(durations):.3f}s / {max(durations):.3f}s")

async def main():

    limits = Limits(max_connections=CONCURRENT_REQUESTS, max_keepalive_connections=5)
    
    async with AsyncClient(base_url=BASE_URL, limits=limits) as client:
        
        #  Chat Interface Batch
        await run_batch(
            client, 
            "/api/v1/chat/chat",
            lambda i: {"messages": [{"role": "user", "content": f"Clinical query {i}"}]},
            "AI Chat Endpoint"
        )
        
        #  RAG Search Batch
        await run_batch(
            client,
            "/api/v1/rag/search",
            lambda i: {"query": "standard protocol for malaria", "top_k": 3},
            "RAG Knowledge Retrieval"
        )

if __name__ == "__main__":
    asyncio.run(main())