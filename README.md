# iOS Community Mega Repo (Unified)

> Automated, unified sideloading repository combining **100+ community sources** (AltStore, SideStore, Feather, Scarlet, and ESign) into a single auto-updating source.

[![Auto-Update](https://github.com/kaiser62/ios-repo-hub/actions/workflows/update.yml/badge.svg)](https://github.com/kaiser62/ios-repo-hub/actions/workflows/update.yml)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live-brightgreen)](https://kaiser62.github.io/ios-repo-hub/)
[![Schedule](https://img.shields.io/badge/Auto--Sync-Every%203%20Hours-blue)](https://github.com/kaiser62/ios-repo-hub/actions)

---

## 🚀 Quick Add to Sideloading Apps

| App | One-Click Install Link | Manual URL |
| :--- | :--- | :--- |
| **SideStore** (Full) | [Add to SideStore](sidestore://source?url=https://kaiser62.github.io/ios-repo-hub/repo.json) | `https://kaiser62.github.io/ios-repo-hub/repo.json` |
| **AltStore** (Full) | [Add to AltStore](altstore://source?url=https://kaiser62.github.io/ios-repo-hub/repo.json) | `https://kaiser62.github.io/ios-repo-hub/repo.json` |
| **SideStore** (Lite) | [Add Lite to SideStore](sidestore://source?url=https://kaiser62.github.io/ios-repo-hub/repo.lite.json) | `https://kaiser62.github.io/ios-repo-hub/repo.lite.json` |
| **AltStore** (Lite) | [Add Lite to AltStore](altstore://source?url=https://kaiser62.github.io/ios-repo-hub/repo.lite.json) | `https://kaiser62.github.io/ios-repo-hub/repo.lite.json` |
| **ESign / Scarlet** | *Copy URL into App* | `https://kaiser62.github.io/ios-repo-hub/repo.esign.json` |
| **Feather** | *Copy URL into Sources* | `https://kaiser62.github.io/ios-repo-hub/repo.json` |

---

## 📦 Feeds Available

- **`repo.json`**: Full master repository formatted with AltStore / SideStore / Feather schema (includes `down` compatibility for ESign).
- **`repo.min.json`**: Minified single-line master JSON for low-bandwidth environments.
- **`repo.lite.json`**: Curated popular tweaked apps (YouTube, Spotify, emulators, sideloaders, social media mods) for faster loading.
- **`repo.esign.json`**: Dedicated ESign schema with direct download mapping.
- **`sources.json`**: Real-time diagnostic status of all 100+ upstream sources, latency, and individual app counts.

---

## ⚙️ How the 3-Hourly Auto-Update Works

1. A GitHub Actions workflow (`.github/workflows/update.yml`) runs on a strict **3-hour cron schedule** (`0 */3 * * *`).
2. Concurrently scrapes all upstream sources with customized User-Agents.
3. Cleans, normalizes, and validates each app object.
4. Performs semantic version comparison per `bundleIdentifier`, keeping the newest release of each app.
5. If changes or updates are detected, automatically commits, pushes to `main`, and deploys to **GitHub Pages**.

---

## 🛠️ Local Development & Manual Build

```bash
# Clone the repository
git clone https://github.com/kaiser62/ios-repo-hub.git
cd ios-repo-hub

# Run the builder
python scripts/build_repo.py
```

## 📄 License
MIT License. All app packages remain property of their respective developers and repositories.
