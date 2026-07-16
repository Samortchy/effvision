"""
pipeline.py
-----------
Runs every combination of (download strategy) x (processing strategy),
times each stage, and produces a comparison table + bar chart.

4 download strategies x 3 processing strategies = 12 combinations.

Usage:
    python pipeline.py --n 20 --out results
    python pipeline.py --n 40 --out results_after_heavier_pic_processing
    python pipeline.py --n 80 --out results_after_heavier_pic_processing_more_pics
"""

import os
import csv
import shutil
import argparse
import itertools
import time

from download_bench import build_urls, STRATEGIES as DOWNLOAD_STRATEGIES
from process_bench import STRATEGIES as PROCESS_STRATEGIES


def time_it(fn, *args, **kwargs):
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, time.perf_counter() - start


def run_pipeline(n_images: int, base_out: str):
    urls = build_urls(n_images)
    results = []

    for dl_name, dl_fn in DOWNLOAD_STRATEGIES.items():
        dl_dir = os.path.join(base_out, "downloads", dl_name)
        if os.path.exists(dl_dir):
            shutil.rmtree(dl_dir)

        print(f"\n=== Download strategy: {dl_name} ===")
        image_paths, dl_time = time_it(dl_fn, urls, dl_dir)
        print(f"  download time: {dl_time:.2f}s")

        for proc_name, proc_fn in PROCESS_STRATEGIES.items():
            proc_dir = os.path.join(base_out, "processed", f"{dl_name}__{proc_name}")
            if os.path.exists(proc_dir):
                shutil.rmtree(proc_dir)

            _, proc_time = time_it(proc_fn, image_paths, proc_dir)
            total = dl_time + proc_time
            print(f"    + process ({proc_name:>15}): {proc_time:6.2f}s  |  total: {total:6.2f}s")

            results.append({
                "download_strategy": dl_name,
                "process_strategy": proc_name,
                "download_time_s": round(dl_time, 3),
                "process_time_s": round(proc_time, 3),
                "total_time_s": round(total, 3),
            })

    return results


def save_csv(results: list[dict], path: str):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)


def plot_results(results: list[dict], path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [f"{r['download_strategy']}\n+ {r['process_strategy']}" for r in results]
    totals = [r["total_time_s"] for r in results]

    # sort by total time so the chart reads best -> worst
    order = sorted(range(len(totals)), key=lambda i: totals[i])
    labels = [labels[i] for i in order]
    totals = [totals[i] for i in order]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(labels, totals, color="#4C72B0")
    ax.set_xlabel("Total time (seconds)")
    ax.set_title("Download + Process strategy combinations (fastest at top)")
    ax.invert_yaxis()
    for bar, total in zip(bars, totals):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2,
                f" {total:.2f}s", va="center", fontsize=8)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Full concurrency benchmark pipeline")
    parser.add_argument("--n", type=int, default=20, help="number of images")
    parser.add_argument("--out", type=str, default="results", help="output directory")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    results = run_pipeline(args.n, args.out)

    csv_path = os.path.join(args.out, "benchmark_results.csv")
    chart_path = os.path.join(args.out, "benchmark_chart.png")
    save_csv(results, csv_path)
    plot_results(results, chart_path)

    print("\n" + "=" * 60)
    print("SUMMARY (sorted fastest -> slowest)")
    print("=" * 60)
    for r in sorted(results, key=lambda r: r["total_time_s"]):
        print(f"{r['download_strategy']:>15} + {r['process_strategy']:<15} "
              f"dl={r['download_time_s']:6.2f}s  proc={r['process_time_s']:6.2f}s  "
              f"total={r['total_time_s']:6.2f}s")

    print(f"\nCSV saved to:   {csv_path}")
    print(f"Chart saved to: {chart_path}")
