#!/usr/bin/env python3
"""
Random Live URL Tester for iOS Community Repo
Picks 500 random app download URLs each run, performs concurrent lightweight
health checks (HEAD or Range GET), records response metrics, and outputs health.json.
"""

import urllib.request
import urllib.error
import json
import random
import concurrent.futures
import time
import os
import sys
import argparse
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
REPO_JSON_PATH = os.path.join(ROOT_DIR, "repo.json")
HEALTH_JSON_PATH = os.path.join(ROOT_DIR, "health.json")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1 AltStore/1.9',
    'Accept': '*/*'
}

def test_single_url(app_info):
    name = app_info.get("name", "Unknown")
    bid = app_info.get("bundleIdentifier", "Unknown")
    url = app_info.get("downloadURL") or app_info.get("down") or ""

    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return {
            "name": name,
            "bundleIdentifier": bid,
            "url": url,
            "alive": False,
            "statusCode": 0,
            "error": "Invalid URL",
            "latencyMs": 0
        }

    t0 = time.time()
    # 1. Try HEAD request first (fastest, transfers 0 body bytes)
    try:
        req = urllib.request.Request(url, headers=HEADERS, method='HEAD')
        with urllib.request.urlopen(req, timeout=8) as resp:
            latency = int((time.time() - t0) * 1000)
            status = resp.getcode()
            is_alive = status in (200, 206, 301, 302, 307, 308)
            return {
                "name": name,
                "bundleIdentifier": bid,
                "url": url,
                "alive": is_alive,
                "statusCode": status,
                "latencyMs": latency,
                "method": "HEAD"
            }
    except urllib.error.HTTPError as e:
        # Many storage providers (GitHub releases, Cloudflare, S3, Catbox) block or reject HEAD with 403 or 405
        if e.code in (403, 405, 503):
            # Fallback to GET with Range 0-512 bytes
            try:
                t1 = time.time()
                get_headers = dict(HEADERS)
                get_headers['Range'] = 'bytes=0-512'
                req_get = urllib.request.Request(url, headers=get_headers, method='GET')
                with urllib.request.urlopen(req_get, timeout=8) as resp_get:
                    latency = int((time.time() - t1) * 1000)
                    status_get = resp_get.getcode()
                    is_alive = status_get in (200, 206, 301, 302, 307, 308)
                    return {
                        "name": name,
                        "bundleIdentifier": bid,
                        "url": url,
                        "alive": is_alive,
                        "statusCode": status_get,
                        "latencyMs": latency,
                        "method": "GET_RANGE"
                    }
            except Exception as e_get:
                latency = int((time.time() - t0) * 1000)
                return {
                    "name": name,
                    "bundleIdentifier": bid,
                    "url": url,
                    "alive": False,
                    "statusCode": getattr(e_get, 'code', 0),
                    "error": str(e_get),
                    "latencyMs": latency
                }
        else:
            latency = int((time.time() - t0) * 1000)
            return {
                "name": name,
                "bundleIdentifier": bid,
                "url": url,
                "alive": False,
                "statusCode": e.code,
                "error": f"HTTP {e.code}",
                "latencyMs": latency
            }
    except Exception as e:
        latency = int((time.time() - t0) * 1000)
        return {
            "name": name,
            "bundleIdentifier": bid,
            "url": url,
            "alive": False,
            "statusCode": 0,
            "error": str(e),
            "latencyMs": latency
        }

def main():
    parser = argparse.ArgumentParser(description="Test 500 random app URLs for liveness")
    parser.add_argument("--sample", type=int, default=500, help="Number of random URLs to test (default: 500)")
    parser.add_argument("--workers", type=int, default=30, help="Concurrent worker threads (default: 30)")
    args = parser.parse_args()

    print("=" * 70)
    print(f"iOS Repo Live URL Tester (Sampling {args.sample} random URLs)")
    print("=" * 70)

    if not os.path.exists(REPO_JSON_PATH):
        print(f"Error: {REPO_JSON_PATH} not found!")
        sys.exit(1)

    with open(REPO_JSON_PATH, "r", encoding="utf-8") as f:
        repo_data = json.load(f)

    apps = repo_data.get("apps", [])
    if not apps:
        print("No apps found in repo.json!")
        sys.exit(1)

    print(f"Total apps in repository: {len(apps)}")
    sample_size = min(args.sample, len(apps))
    sampled_apps = random.sample(apps, sample_size)
    print(f"Randomly selected {sample_size} apps to test with {args.workers} workers...")

    start_time = time.time()
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        for res in executor.map(test_single_url, sampled_apps):
            results.append(res)
            # Show live progress
            if len(results) % 50 == 0 or len(results) == sample_size:
                alive_so_far = sum(1 for r in results if r["alive"])
                print(f"Progress: {len(results)}/{sample_size} tested — {alive_so_far} alive ({alive_so_far/len(results)*100:.1f}%)")

    total_time = round(time.time() - start_time, 2)
    alive_items = [r for r in results if r["alive"]]
    dead_items = [r for r in results if not r["alive"]]
    alive_pct = round((len(alive_items) / sample_size) * 100, 2)
    avg_latency = round(sum(r["latencyMs"] for r in alive_items) / max(len(alive_items), 1))

    print("\n" + "=" * 70)
    print(f"Live URL Test Results ({total_time}s):")
    print(f"- Total Sampled: {sample_size}")
    print(f"- Live / Accessible: {len(alive_items)} ({alive_pct}%)")
    print(f"- Dead / Inaccessible: {len(dead_items)}")
    print(f"- Average Latency: {avg_latency} ms")
    print("=" * 70)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    health_report = {
        "testedAt": now_iso,
        "sampleSize": sample_size,
        "aliveCount": len(alive_items),
        "deadCount": len(dead_items),
        "alivePercentage": alive_pct,
        "avgLatencyMs": avg_latency,
        "totalRepositoryApps": len(apps),
        "recentDead": dead_items[:30], # Top 30 dead for quick inspection
        "samples": results[:50] # Preview of tested items
    }

    with open(HEALTH_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(health_report, f, indent=2)

    print(f"Health report written to {HEALTH_JSON_PATH}")

if __name__ == "__main__":
    main()
