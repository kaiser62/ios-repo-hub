#!/usr/bin/env python3
"""
iOS Unified Community Repository Builder & Aggregator
Merges 100+ AltStore, SideStore, Feather, and ESign sources into unified,
deduplicated JSON feeds with automated 3-hourly GitHub Actions synchronization.
"""

import urllib.request
import urllib.error
import json
import concurrent.futures
import re
import os
import sys
import time
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
SOURCES_FILE = os.path.join(SCRIPT_DIR, "sources.txt")

HEADERS = {
    'User-Agent': 'AltStore/1.9.0 (iOS 17.0; iPhone15,2; SideStore/0.5.8)',
    'Accept': 'application/json, text/plain, */*'
}

def clean_url(url: str) -> str:
    u = url.strip()
    if 'github.com' in u and '/raw/' in u:
        u = u.replace('github.com', 'raw.githubusercontent.com').replace('/raw/', '/')
    return u

def fetch_single_source(url: str):
    cleaned = clean_url(url)
    t0 = time.time()
    req = urllib.request.Request(cleaned, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=14) as resp:
            data = resp.read()
            text = data.decode('utf-8', errors='ignore')
            obj = json.loads(text)
            duration = round(time.time() - t0, 2)
            return {"url": url, "status": "ok", "data": obj, "duration": duration}
    except Exception as e:
        duration = round(time.time() - t0, 2)
        return {"url": url, "status": "error", "error": str(e), "duration": duration}

def parse_version_tuple(v: str):
    if not v:
        return (0,)
    nums = re.findall(r'\d+', str(v))
    return tuple(int(n) for n in nums) if nums else (0,)

def is_valid_url(u: str) -> bool:
    if not u or not isinstance(u, str):
        return False
    return u.startswith('http://') or u.startswith('https://')

def normalize_app(app: dict, source_url: str):
    # Extract name
    name = app.get("name") or app.get("title") or app.get("bundleName") or ""
    name = str(name).strip()
    if not name:
        return None

    # Extract bundle ID
    bid = app.get("bundleIdentifier") or app.get("bundleID") or app.get("package") or app.get("id") or ""
    bid = str(bid).strip()
    if not bid:
        # Fallback slug
        bid = "com.community." + re.sub(r'[^a-zA-Z0-9]', '.', name.lower()).strip('.')

    # Extract download URL (AltStore downloadURL vs ESign down)
    down_url = app.get("downloadURL") or app.get("down") or app.get("url") or app.get("link") or ""
    down_url = str(down_url).strip()
    if not is_valid_url(down_url):
        return None

    # Extract version
    version = app.get("version") or app.get("versionString") or "1.0"
    version = str(version).strip()

    # Extract date
    version_date = app.get("versionDate") or app.get("date") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Extract description
    desc = app.get("localizedDescription") or app.get("description") or app.get("subtitle") or ""
    desc = str(desc).strip()

    # Extract icon
    icon = app.get("iconURL") or app.get("icon") or app.get("icon_url") or ""
    icon = str(icon).strip()
    if not is_valid_url(icon):
        icon = "https://raw.githubusercontent.com/LiveContainer/LiveContainer/main/screenshots/icon.png"

    # Extract size
    size = app.get("size") or 0
    try:
        size = int(size)
    except:
        size = 0

    developer = app.get("developerName") or app.get("author") or app.get("developer") or "Community Developer"
    tint = app.get("tintColor") or "#007AFF"

    screenshots = app.get("screenshotURLs") or app.get("screenshots") or []
    if not isinstance(screenshots, list):
        screenshots = []

    return {
        "name": name,
        "bundleIdentifier": bid,
        "developerName": str(developer).strip(),
        "version": version,
        "versionDate": str(version_date),
        "versionDescription": str(app.get("versionDescription") or f"Release {version}"),
        "downloadURL": down_url,
        "down": down_url, # ESign compatibility
        "localizedDescription": desc,
        "iconURL": icon,
        "icon": icon, # ESign compatibility
        "tintColor": str(tint),
        "size": size,
        "screenshotURLs": [s for s in screenshots if is_valid_url(s)],
        "source": source_url
    }

def main():
    print("=" * 70)
    print("Starting iOS Unified Community Repository Generation")
    print("=" * 70)

    if not os.path.exists(SOURCES_FILE):
        print(f"Error: {SOURCES_FILE} not found!")
        sys.exit(1)

    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        sources = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"Loaded {len(sources)} sources to query concurrently...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        results = list(executor.map(fetch_single_source, sources))

    source_stats = []
    apps_by_bid = {}
    total_raw_apps = 0

    for r in results:
        url = r["url"]
        status = r["status"]
        duration = r["duration"]

        if status != "ok":
            source_stats.append({
                "url": url,
                "status": "error",
                "error": r.get("error", "Unknown error"),
                "duration": duration,
                "appCount": 0
            })
            continue

        data = r["data"]
        raw_items = []
        if isinstance(data, dict):
            if "apps" in data and isinstance(data["apps"], list):
                raw_items = data["apps"]
            elif "app" in data and isinstance(data["app"], list):
                raw_items = data["app"]
            elif "packages" in data and isinstance(data["packages"], list):
                raw_items = data["packages"]
        elif isinstance(data, list):
            raw_items = data

        parsed_count = 0
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            app = normalize_app(item, url)
            if not app:
                continue
            total_raw_apps += 1
            parsed_count += 1
            bid = app["bundleIdentifier"].lower()

            if bid not in apps_by_bid:
                apps_by_bid[bid] = app
            else:
                existing = apps_by_bid[bid]
                v_new = parse_version_tuple(app["version"])
                v_old = parse_version_tuple(existing["version"])
                if v_new > v_old:
                    apps_by_bid[bid] = app
                elif v_new == v_old and len(app.get("localizedDescription", "")) > len(existing.get("localizedDescription", "")):
                    apps_by_bid[bid] = app

        source_stats.append({
            "url": url,
            "status": "online",
            "duration": duration,
            "appCount": parsed_count
        })

    unique_apps = list(apps_by_bid.values())
    unique_apps.sort(key=lambda a: a["name"].lower())

    print(f"\nFetch Summary:")
    print(f"- Total Sources Scraped: {len(sources)}")
    print(f"- Active Sources: {sum(1 for s in source_stats if s['status'] == 'online')}")
    print(f"- Total Raw Apps Extracted: {total_raw_apps}")
    print(f"- Deduplicated Unique Apps: {len(unique_apps)}")

    # Curate Top / Popular Apps for lite feed
    POPULAR_KEYWORDS = [
        "youtube", "ytlite", "uyou", "spotify", "eevee", "spotilife",
        "delta", "provenance", "flycast", "ppsspp", "retroarch", "utm",
        "sidestore", "livecontainer", "stikdebug", "feather", "cowabunga",
        "trollstore", "twitter", "bhtwitter", "instagram", "rocket",
        "tiktok", "bhtiktok", "apollo", "reddit", "winston", "enmity",
        "discord", "itorrent", "ish", "vlc", "kodi", "streamer", "infuse"
    ]

    lite_apps = []
    for app in unique_apps:
        search_blob = f"{app['name']} {app['bundleIdentifier']} {app['localizedDescription']}".lower()
        if any(kw in search_blob for kw in POPULAR_KEYWORDS):
            lite_apps.append(app)
        elif len(lite_apps) < 400 and (app.get("screenshotURLs") or len(app.get("localizedDescription", "")) > 50):
            lite_apps.append(app)

    lite_apps.sort(key=lambda a: a["name"].lower())
    print(f"- Curated Lite Apps: {len(lite_apps)}")

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. Full Master AltStore / SideStore Repo
    master_repo = {
        "name": "iOS Community Mega Repo (Unified)",
        "identifier": "com.kaiser62.ios-community-repo",
        "subtitle": "Unified community repository aggregated from 100+ sources",
        "description": "Comprehensive iOS sideloading source combining AltStore, SideStore, Feather, and ESign libraries into a single auto-updating hub.",
        "iconURL": "https://raw.githubusercontent.com/LiveContainer/LiveContainer/main/screenshots/icon.png",
        "website": "https://kaiser62.github.io/ios-repo-hub/",
        "version": "2.0.0",
        "updated": now_iso,
        "apps": unique_apps,
        "news": [
            {
                "title": "Repo Auto-Updated",
                "identifier": f"update-{int(time.time())}",
                "caption": f"Updated with {len(unique_apps)} unique sideloadable apps",
                "date": now_iso,
                "tintColor": "#007AFF"
            }
        ]
    }

    # 2. Curated Lite Repo
    lite_repo = dict(master_repo)
    lite_repo["name"] = "iOS Community Mega Repo (Lite / Curated)"
    lite_repo["identifier"] = "com.kaiser62.ios-community-repo.lite"
    lite_repo["apps"] = lite_apps

    # 3. ESign Dedicated Schema
    esign_repo = {
        "name": "iOS Community Mega Repo (ESign)",
        "identifier": "com.kaiser62.ios-community-repo.esign",
        "updated": now_iso,
        "apps": unique_apps
    }

    # Write files
    repo_json_path = os.path.join(ROOT_DIR, "repo.json")
    repo_min_path = os.path.join(ROOT_DIR, "repo.min.json")
    repo_lite_path = os.path.join(ROOT_DIR, "repo.lite.json")
    repo_esign_path = os.path.join(ROOT_DIR, "repo.esign.json")
    sources_json_path = os.path.join(ROOT_DIR, "sources.json")

    print(f"\nWriting output files...")
    with open(repo_json_path, "w", encoding="utf-8") as f:
        json.dump(master_repo, f, indent=2, ensure_ascii=False)
    print(f"-> {repo_json_path} ({os.path.getsize(repo_json_path) / (1024*1024):.2f} MB)")

    with open(repo_min_path, "w", encoding="utf-8") as f:
        json.dump(master_repo, f, separators=(',', ':'), ensure_ascii=False)
    print(f"-> {repo_min_path} ({os.path.getsize(repo_min_path) / (1024*1024):.2f} MB)")

    with open(repo_lite_path, "w", encoding="utf-8") as f:
        json.dump(lite_repo, f, indent=2, ensure_ascii=False)
    print(f"-> {repo_lite_path} ({os.path.getsize(repo_lite_path) / (1024*1024):.2f} MB)")

    with open(repo_esign_path, "w", encoding="utf-8") as f:
        json.dump(esign_repo, f, indent=2, ensure_ascii=False)
    print(f"-> {repo_esign_path} ({os.path.getsize(repo_esign_path) / (1024*1024):.2f} MB)")

    with open(sources_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "updated": now_iso,
            "totalSources": len(sources),
            "onlineSources": sum(1 for s in source_stats if s['status'] == 'online'),
            "totalApps": len(unique_apps),
            "sources": source_stats
        }, f, indent=2)
    print(f"-> {sources_json_path}")

    print("\nRepo generation completed successfully!")

if __name__ == "__main__":
    main()
