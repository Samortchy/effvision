"""
download_bench.py
------------------
I/O-BOUND TASK: downloading images from the web.

Why I/O-bound? The CPU spends almost all its time *waiting* on the network
(DNS lookup, TCP handshake, waiting for bytes to arrive). While a thread is
waiting on a socket, Python releases the GIL -- so other threads can run.
That's why threading and asyncio shine here, while multiprocessing (which
pays heavy process-creation cost for no CPU benefit) usually does NOT.

Four strategies implemented, same task, same inputs:
    1. sequential        - one request after another (baseline)
    2. threaded          - concurrent.futures.ThreadPoolExecutor
    3. multiprocessing    - concurrent.futures.ProcessPoolExecutor (control group --
                            included so you can SEE it's the wrong tool here)
    4. asyncio            - aiohttp, single-threaded event loop

Images come from https://picsum.photos (a free placeholder image service).
Each image gets a unique seed so URLs don't collide with caching.
"""

import os
import time
import asyncio
import requests
import aiohttp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


def build_urls(n: int, width: int = 800, height: int = 600) -> list[str]:
    """Build n distinct picsum.photos URLs (distinct seed = distinct image)."""
    return [f"https://picsum.photos/seed/{i}/{width}/{height}" for i in range(n)]


def _download_one(url: str, out_dir: str) -> str:
    """Download a single URL to out_dir. Used by sequential/threaded/multiproc."""
    idx = url.rsplit("/seed/", 1)[1].split("/")[0]
    path = os.path.join(out_dir, f"img_{idx}.jpg")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    with open(path, "wb") as f:
        f.write(resp.content)
    return path


# ---------------------------------------------------------------------------
# 1. Sequential
# ---------------------------------------------------------------------------
def download_sequential(urls: list[str], out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    return [_download_one(u, out_dir) for u in urls]


# ---------------------------------------------------------------------------
# 2. Threading
# ---------------------------------------------------------------------------
def download_threaded(urls: list[str], out_dir: str, max_workers: int = 16) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(lambda u: _download_one(u, out_dir), urls))


# ---------------------------------------------------------------------------
# 3. Multiprocessing (control group -- expect this to be slow: process
#    startup overhead dominates since there's barely any CPU work per task)
# ---------------------------------------------------------------------------
def _mp_worker(args):
    url, out_dir = args
    return _download_one(url, out_dir)


def download_multiprocessing(urls: list[str], out_dir: str, max_workers: int = os.cpu_count()) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(_mp_worker, [(u, out_dir) for u in urls]))


# ---------------------------------------------------------------------------
# 4. Asyncio (aiohttp) -- usually the fastest + most memory-efficient for
#    many small I/O-bound requests, since there's no thread/process overhead.
# ---------------------------------------------------------------------------
async def _async_download_one(session: aiohttp.ClientSession, url: str, out_dir: str) -> str:
    idx = url.rsplit("/seed/", 1)[1].split("/")[0]
    path = os.path.join(out_dir, f"img_{idx}.jpg")
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        data = await resp.read()
    with open(path, "wb") as f:
        f.write(data)
    return path


async def _download_async_main(urls: list[str], out_dir: str) -> list[str]:
    async with aiohttp.ClientSession() as session:
        tasks = [_async_download_one(session, u, out_dir) for u in urls] #task[0], task[1],...
        return await asyncio.gather(*tasks)


def download_async(urls: list[str], out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    return asyncio.run(_download_async_main(urls, out_dir))


# ---------------------------------------------------------------------------
# Standalone benchmark (run this file directly to compare download strategies alone)
# ---------------------------------------------------------------------------
STRATEGIES = {
    "sequential": download_sequential,
    "threaded": download_threaded,
    "multiprocessing": download_multiprocessing,
    "asyncio": download_async,
}


def time_it(fn, *args, **kwargs):
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, time.perf_counter() - start


if __name__ == "__main__":
    import argparse
    import shutil

    parser = argparse.ArgumentParser(description="Benchmark download concurrency strategies")
    parser.add_argument("--n", type=int, default=20, help="number of images to download")
    parser.add_argument("--out", type=str, default="downloads_bench", help="base output dir")
    args = parser.parse_args()

    urls = build_urls(args.n)
    print(f"Benchmarking download of {args.n} images with 4 strategies...\n")

    for name, fn in STRATEGIES.items():
        out_dir = os.path.join(args.out, name)
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        _, elapsed = time_it(fn, urls, out_dir)
        print(f"{name:>18}: {elapsed:6.2f}s")