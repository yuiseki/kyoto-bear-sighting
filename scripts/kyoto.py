"""Shared helpers: the クマ目撃情報 of Kyoto Prefecture (BODIK open data catalogue) and how to read the CSV."""

import csv
import datetime as dt
import io

CKAN = "https://data.bodik.jp"
PACKAGE = "260002_bear"
PACKAGE_URL = f"{CKAN}/dataset/{PACKAGE}"
API_PACKAGE = f"{CKAN}/api/3/action/package_show?id={PACKAGE}"
LICENSE_ID = "cc-by-40-intl"
CSV_RESOURCE = "260002bearfy.csv"  # the integrated file, FY2009 to FY2018
COLUMNS = [
    "時間軸コード", "年度", "観察場所", "環境区分", "経度", "緯度", "目撃年月日", "成獣(匹)",
    "幼獣(匹)", "その他(匹)", "目撃時の状況", "個体の状況", "その後の処置", "市町村コード",
    "市町村コード（6桁）", "市町村名",
]  # fmt: skip
BBOX = (134.5, 34.6, 136.2, 35.9)  # lon min, lat min, lon max, lat max: Kyoto with a margin


def fiscal_year(d: dt.date) -> int:
    return d.year if d.month >= 4 else d.year - 1


def parse_csv(data: bytes) -> list[dict]:
    """The records with the source's columns as stripped strings (the source pads numbers with a space);
    checks the header, the dates, the coordinates and that the year column is the fiscal year of the date."""
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline="")))
    if not rows or list(rows[0]) != COLUMNS:
        raise ValueError(f"unexpected header {list(rows[0]) if rows else None}")
    out = []
    for i, r in enumerate(rows):
        if None in r or None in r.values():
            raise ValueError(f"row {i}: ragged")
        v = {c: x.strip() for c, x in r.items()}
        d = dt.date.fromisoformat(v["目撃年月日"])
        lon, lat = float(v["経度"]), float(v["緯度"])
        if not (BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]):
            raise ValueError(f"row {i}: point outside Kyoto ({lat}, {lon})")
        if fiscal_year(d) != int(v["年度"]):
            raise ValueError(f"row {i}: 年度 {v['年度']} is not the fiscal year of {d}")
        v["_date"], v["_lon"], v["_lat"] = d, lon, lat
        out.append(v)
    return out
