"""Download the クマ目撃情報 (integrated CSV, FY2009 to FY2018) of Kyoto Prefecture from the BODIK catalogue.

Saves the catalogue's metadata (package_show) and the integrated CSV as served, with sha256 and the
Last-Modified, in data/raw/<version>/MANIFEST.json. Stops when the catalogue does not say
cc-by-40-intl. The version is the UTC date of the run.

    uv run python scripts/01_download.py [--version 2026-10-26]
"""

import argparse
import datetime as dt
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

import kyoto as k

ROOT = Path(__file__).parents[1]
UA = "kyoto-bear-sighting/0.1 (+https://github.com/yuiseki/kyoto-bear-sighting)"


def get(url: str) -> tuple[bytes, dict]:
    with urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120
    ) as r:
        return r.read(), {h.lower(): v for h, v in r.headers.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=dt.datetime.now(dt.UTC).strftime("%Y-%m-%d"))
    args = ap.parse_args()
    raw = ROOT / "data" / "raw" / args.version
    raw.mkdir(parents=True, exist_ok=True)
    body, _ = get(k.API_PACKAGE)
    pkg = json.loads(body)["result"]
    if pkg["license_id"] != k.LICENSE_ID:
        raise SystemExit(f"license_id is {pkg['license_id']!r}, not {k.LICENSE_ID}: stopping")
    (raw / "package.json").write_bytes(body)
    res = [r for r in pkg["resources"] if r["url"].endswith("/" + k.CSV_RESOURCE)]
    if len(res) != 1:
        raise SystemExit(f"expected one resource named {k.CSV_RESOURCE}, found {len(res)}")
    r = res[0]
    time.sleep(1)
    data, h = get(r["url"])
    (raw / k.CSV_RESOURCE).write_bytes(data)
    manifest = {
        "retrieved": args.version, "page": k.PACKAGE_URL, "title": pkg["title"],
        "license_id": pkg["license_id"], "organization": pkg["organization"]["title"],
        "metadata_modified": pkg["metadata_modified"], "resource_name": r["name"],
        "resource_description": r.get("description"), "resource_last_modified": r["last_modified"],
        "files": {
            k.CSV_RESOURCE: {"url": r["url"], "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                             "last_modified": h.get("last-modified")},
            "package.json": {"url": k.API_PACKAGE, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()},
        },
    }  # fmt: skip
    (raw / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(pkg["title"], len(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
