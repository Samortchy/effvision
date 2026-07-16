"""
process_bench.py
-----------------
CPU-BOUND TASK: heavy image processing.

Why CPU-bound? The work here is pure computation (pixel math), not waiting
on anything external. CPython's GIL means only ONE thread can execute
Python bytecode at a time -- so for pure-Python CPU work, threading gives
*no* speedup (often a slight slowdown from context-switch overhead).
Multiprocessing sidesteps the GIL entirely by using separate processes,
each with its own interpreter and its own GIL, so it scales with CPU cores.

To make this an honest demo we deliberately include a hand-written pixel
loop (`_manual_convolution`) instead of relying only on Pillow's built-in
filters. Pillow's C-level filters (GaussianBlur, etc.) release the GIL
internally, so threading *would* show some speedup there -- which is a
subtler, equally important lesson, and we surface it separately.

Three strategies implemented, same task, same inputs:
    1. sequential      - one image after another (baseline)
    2. threaded        - concurrent.futures.ThreadPoolExecutor (expect ~no
                          speedup on the pure-Python part -- that's the GIL)
    3. multiprocessing  - concurrent.futures.ProcessPoolExecutor (expect
                          near-linear speedup with core count)

(asyncio is intentionally NOT implemented here -- asyncio only helps
concurrency for I/O waits; it has nothing to offer pure CPU-bound work.)
"""

import os
import time
from PIL import Image, ImageFilter
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


def _manual_convolution(pixels: list, width: int, height: int) -> list:
    """
    A deliberately slow, pure-Python 3x3 edge-detection convolution.
    This is the part that is GENUINELY GIL-bound: no C extension releases
    the GIL here, it's all Python bytecode. This is what best demonstrates
    why threading doesn't help CPU-bound pure-Python work.
    """
    kernel = [-1, -1, -1, -1, 8, -1, -1, -1, -1]
    out = [0] * (width * height)
    for y in range(1, height - 1):
        row_offset = y * width
        for x in range(1, width - 1):
            idx = row_offset + x
            acc = (
                pixels[idx - width - 1] * kernel[0] + pixels[idx - width] * kernel[1] + pixels[idx - width + 1] * kernel[2]
                + pixels[idx - 1] * kernel[3] + pixels[idx] * kernel[4] + pixels[idx + 1] * kernel[5]
                + pixels[idx + width - 1] * kernel[6] + pixels[idx + width] * kernel[7] + pixels[idx + width + 1] * kernel[8]
            )
            out[idx] = max(0, min(255, acc))
    return out


def heavy_process(image_path: str, out_dir: str, manual_size: tuple = (300, 225), passes: int = 2) -> str:
    """
    The full "heavy" pipeline applied to one image:
      1. Pillow filter chain (C-accelerated: blur, detail, edge enhance)
      2. A hand-written pure-Python convolution on a downsized copy, run
         `passes` times (this is the genuinely GIL-bound, CPU-heavy part)
      3. Save the result
    """
    img = Image.open(image_path).convert("RGB")

    # Step 1: Pillow C-level filters (these DO release the GIL internally)
    img = img.filter(ImageFilter.GaussianBlur(radius=3))
    img = img.filter(ImageFilter.DETAIL)
    img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)

    # Step 2: pure-Python convolution on a small grayscale copy (GIL-bound)
    small = img.convert("L").resize(manual_size)
    w, h = small.size
    pixels = list(small.getdata())
    for _ in range(passes):
        pixels = _manual_convolution(pixels, w, h)
    small.putdata(pixels)

    # Step 3: paste processed thumbnail onto a corner of the full image and save
    result = img.copy()
    result.paste(small.convert("RGB"), (0, 0))

    out_path = os.path.join(out_dir, os.path.basename(image_path))
    result.save(out_path)
    return out_path


# ---------------------------------------------------------------------------
# 1. Sequential
# ---------------------------------------------------------------------------
def process_sequential(image_paths: list[str], out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    return [heavy_process(p, out_dir, manual_size=(600, 450), passes=4) for p in image_paths]


# ---------------------------------------------------------------------------
# 2. Threading
# ---------------------------------------------------------------------------
def process_threaded(image_paths: list[str], out_dir: str, max_workers: int = os.cpu_count()) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(lambda p: heavy_process(p, out_dir), image_paths))


# ---------------------------------------------------------------------------
# 3. Multiprocessing
# ---------------------------------------------------------------------------
def _mp_worker(args):
    path, out_dir = args
    return heavy_process(path, out_dir, manual_size=(600, 450), passes=4)


def process_multiprocessing(image_paths: list[str], out_dir: str, max_workers: int | None = None) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(_mp_worker, [(p, out_dir) for p in image_paths], chunksize=4))


# ---------------------------------------------------------------------------
# Standalone benchmark (run this file directly against a folder of images)
# ---------------------------------------------------------------------------
STRATEGIES = {
    "sequential": process_sequential,
    "threaded": process_threaded,
    "multiprocessing": process_multiprocessing,
}


def time_it(fn, *args, **kwargs):
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, time.perf_counter() - start


if __name__ == "__main__":
    import argparse
    import shutil
    import glob

    parser = argparse.ArgumentParser(description="Benchmark image-processing concurrency strategies")
    parser.add_argument("--input", type=str, required=True, help="folder of input images")
    parser.add_argument("--out", type=str, default="processed_bench", help="base output dir")
    args = parser.parse_args()

    paths = sorted(glob.glob(os.path.join(args.input, "*.jpg")) + glob.glob(os.path.join(args.input, "*.png")))
    if not paths:
        raise SystemExit(f"No images found in {args.input}")

    print(f"Benchmarking processing of {len(paths)} images with 3 strategies...\n")

    for name, fn in STRATEGIES.items():
        out_dir = os.path.join(args.out, name)
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        _, elapsed = time_it(fn, paths, out_dir)
        print(f"{name:>18}: {elapsed:6.2f}s")
