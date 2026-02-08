"""
Bulk download US Congressional Bills (PDF) from GovInfo.gov.

These are public domain legal documents from the 118th US Congress.
URL pattern: https://www.govinfo.gov/content/pkg/BILLS-118hr{N}ih/pdf/BILLS-118hr{N}ih.pdf

Usage:
    python data/download_legal_pdfs.py --target 1000
"""

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

SOURCE_DIR = Path(__file__).parent / "source"
BASE_URL = "https://www.govinfo.gov/content/pkg/BILLS-118hr{n}{ver}/pdf/BILLS-118hr{n}{ver}.pdf"

# Bill versions to try: ih=introduced, enr=enrolled, eh=engrossed
VERSIONS = ["ih", "enr", "eh", "rfs", "rs"]


def download_one(bill_number: int, dest_dir: Path) -> str | None:
    """Try to download a single bill PDF. Returns filename on success, None on failure."""
    for ver in VERSIONS:
        url = BASE_URL.format(n=bill_number, ver=ver)
        filename = f"BILLS-118hr{bill_number}{ver}.pdf"
        filepath = dest_dir / filename
        if filepath.exists():
            return filename  # already downloaded

        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/pdf"):
                filepath.write_bytes(resp.content)
                return filename
        except requests.RequestException:
            continue
    return None


def main():
    parser = argparse.ArgumentParser(description="Download US Congressional Bill PDFs from GovInfo")
    parser.add_argument("--target", type=int, default=1000, help="Target number of PDFs to download")
    parser.add_argument("--workers", type=int, default=8, help="Number of parallel download threads")
    parser.add_argument("--dest", default=str(SOURCE_DIR), help="Destination directory")
    args = parser.parse_args()

    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)

    existing = len(list(dest.glob("*.pdf")))
    print(f"Existing PDFs in {dest}: {existing}")

    target = args.target
    downloaded = existing
    bill_number = 1
    max_bill = 10000  # 118th Congress has bills up to ~9000+

    print(f"Target: {target} PDFs | Workers: {args.workers}")
    print("Downloading US Congressional Bills (118th Congress) from GovInfo.gov ...\n")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {}
        batch_size = min(200, target - downloaded + 50)

        while downloaded < target and bill_number <= max_bill:
            # Submit a batch
            while len(futures) < batch_size and bill_number <= max_bill:
                fut = pool.submit(download_one, bill_number, dest)
                futures[fut] = bill_number
                bill_number += 1

            # Collect completed
            done = [f for f in futures if f.done()]
            for fut in done:
                bn = futures.pop(fut)
                result = fut.result()
                if result:
                    downloaded += 1
                    if downloaded % 50 == 0 or downloaded == target:
                        print(f"  [{downloaded}/{target}] downloaded (latest: {result})")
                    if downloaded >= target:
                        break

            if not done:
                time.sleep(0.1)

        # Cancel remaining futures
        for fut in futures:
            fut.cancel()

    print(f"\nDone! Total PDFs in {dest}: {len(list(dest.glob('*.pdf')))}")


if __name__ == "__main__":
    main()
