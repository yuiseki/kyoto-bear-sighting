"""Check the Parquet against the CSV as served, with pyarrow's CSV reader (all columns as strings).

Every row: each text column equals the CSV's text with the padding stripped (an empty field is null),
the year, the coordinates and the date equal the CSV's, the point equals the coordinates. Also: the row
total equals the CSV's and the sha256 of the CSV equals the manifest's.

    uv run python scripts/03_verify.py
"""

import datetime as dt
import hashlib
import importlib
import json
import sys
from pathlib import Path

import kyoto as k
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
from shapely import from_wkb

ROOT = Path(__file__).parents[1]


def main() -> int:
    exp = importlib.import_module("02_export_parquet")
    run = sorted((ROOT / "data" / "raw").glob("*/MANIFEST.json"))[-1].parent
    manifest = json.loads((run / "MANIFEST.json").read_text())
    path = run / k.CSV_RESOURCE
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest() == manifest["files"][k.CSV_RESOURCE]["sha256"]
    )
    src = pacsv.read_csv(
        path,
        read_options=pacsv.ReadOptions(encoding="utf-8"),
        parse_options=pacsv.ParseOptions(newlines_in_values=True),
        convert_options=pacsv.ConvertOptions(
            column_types={c: "string" for c in k.COLUMNS}, strings_can_be_null=False
        ),
    ).to_pydict()
    t = pq.read_table(ROOT / "data" / "parquet" / "sighting.parquet")
    d = t.to_pydict()
    n = len(src["年度"])
    assert t.num_rows == n, (t.num_rows, n)
    for i in range(n):
        for c, col in exp.TEXT.items():
            assert d[col][i] == (src[c][i].strip() or None), (i, c)
        assert d["fiscal_year"][i] == int(src["年度"][i].strip()), i
        assert d["longitude"][i] == float(src["経度"][i]) and d["latitude"][i] == float(
            src["緯度"][i]
        ), i
        assert d["date"][i] == dt.date.fromisoformat(src["目撃年月日"][i].strip()), i
        g = from_wkb(d["geometry"][i])
        assert (g.x, g.y) == (d["longitude"][i], d["latitude"][i]), i
    print(f"OK: {n} rows equal the CSV")
    return 0


if __name__ == "__main__":
    sys.exit(main())
