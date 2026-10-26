"""Write GeoParquet of the クマ目撃情報 of Kyoto Prefecture (the integrated CSV, FY2009 to FY2018).

One row per record. The source's columns, as stripped strings (the source pads numbers with a space):
time_axis_code (時間軸コード), fiscal_year (年度, integer), place (観察場所), environment (環境区分),
longitude, latitude (floats), date (目撃年月日), adults_text, juveniles_text, others_text (成獣, 幼獣,
その他 (匹): text, because the source has `不明` and, once, a sentence there), situation (目撃時の状況),
individual_status (個体の状況), action (その後の処置), municipality_code (5 digits), municipality_code6,
municipality, geometry (WKB Point, WGS84 assumed). Empty fields are null.

    uv run python scripts/02_export_parquet.py [--version 2026-10-26]
"""

import argparse
import json
import sys
from pathlib import Path

import kyoto as k
import pyarrow as pa
import pyarrow.parquet as pq
from shapely.geometry import Point

ROOT = Path(__file__).parents[1]
TEXT = {  # CSV column -> Parquet column
    "時間軸コード": "time_axis_code", "観察場所": "place", "環境区分": "environment",
    "成獣(匹)": "adults_text", "幼獣(匹)": "juveniles_text", "その他(匹)": "others_text",
    "目撃時の状況": "situation", "個体の状況": "individual_status", "その後の処置": "action",
    "市町村コード": "municipality_code", "市町村コード（6桁）": "municipality_code6",
    "市町村名": "municipality",
}  # fmt: skip
SCHEMA = pa.schema(
    [
        ("time_axis_code", pa.string()), ("fiscal_year", pa.int16()), ("place", pa.string()),
        ("environment", pa.string()), ("longitude", pa.float64()), ("latitude", pa.float64()),
        ("date", pa.date32()), ("adults_text", pa.string()), ("juveniles_text", pa.string()),
        ("others_text", pa.string()), ("situation", pa.string()), ("individual_status", pa.string()),
        ("action", pa.string()), ("municipality_code", pa.string()), ("municipality_code6", pa.string()),
        ("municipality", pa.string()), ("geometry", pa.binary()),
    ]
)  # fmt: skip


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=None)
    args = ap.parse_args()
    runs = sorted((ROOT / "data" / "raw").glob("*/MANIFEST.json"))
    raw = runs[-1].parent if args.version is None else ROOT / "data" / "raw" / args.version
    rows = k.parse_csv((raw / k.CSV_RESOURCE).read_bytes())
    data = {col: [r[c] or None for r in rows] for c, col in TEXT.items()}
    data["fiscal_year"] = [int(r["年度"]) for r in rows]
    data["longitude"] = [r["_lon"] for r in rows]
    data["latitude"] = [r["_lat"] for r in rows]
    data["date"] = [r["_date"] for r in rows]
    data["geometry"] = [Point(r["_lon"], r["_lat"]).wkb for r in rows]
    geo = {"version": "1.1.0", "primary_column": "geometry",
           "columns": {"geometry": {"encoding": "WKB", "geometry_types": ["Point"]}}}  # fmt: skip
    t = pa.table({f.name: data[f.name] for f in SCHEMA}, schema=SCHEMA)
    t = t.replace_schema_metadata({b"geo": json.dumps(geo).encode()})
    out = ROOT / "data" / "parquet"
    out.mkdir(parents=True, exist_ok=True)
    pq.write_table(t, out / "sighting.parquet", compression="zstd")
    (out / "columns.json").write_text(
        json.dumps({"run": raw.name, "rows": len(rows)}, indent=2) + "\n"
    )
    print(len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
