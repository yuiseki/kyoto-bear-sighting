"""Write data/README.md (the dataset card), data/LICENSE and data/provenance.yaml.

uv run python scripts/04_card.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

import kyoto as k
import pyarrow.parquet as pq

ROOT = Path(__file__).parents[1]
REPO = "kyoto-bear-sighting"

CARD = """---
license: cc-by-4.0
license_name: cc-by-4.0
license_link: https://creativecommons.org/licenses/by/4.0/legalcode.ja
language:
- ja
tags:
- japan
- kyoto
- bear
- wildlife
- geospatial
size_categories:
- 10K<n<100K
pretty_name: Bear sightings of Kyoto Prefecture (クマ目撃情報, FY2009 to FY2018)
---

# {repo}

The bear (ツキノワグマ) sighting records of Kyoto Prefecture, FY2009 to FY2018 (from {first} to
{last}), as the prefecture's information policy division published them in the BODIK open data
catalogue: {rows:,} records, each with the place, the environment, the number of adults, juveniles
and others, the situation and the action taken. As GeoParquet. The catalogue has not been updated
since {meta_modified}; there is nothing here after December 2018.

## Source

- Catalogue entry: <{page}> ({org}, データ提供元 on BODIK), titled 「{title}」, licence `{license_id}`
  (Creative Commons Attribution 4.0 International), metadata last modified {meta_modified}.
- File: `{csv}` as served, the integrated file (統合版) of FY2009 to FY2018, the catalogue's own
  description: 「{res_desc}」 (UTF-8 with a byte order mark; {csv_bytes:,} bytes), kept unchanged under
  `raw/{run}/` with its sha256 in `MANIFEST.json`, with the catalogue's `package.json`. Fetched
  {fetched}; the file was last modified {res_modified} according to the catalogue. The catalogue also
  has one CSV per fiscal year, an XLSX, an RDF, and an older file of FY2016; they were not downloaded.

## Files

| Path | Content |
|---|---|
| `parquet/sighting.parquet` | all {rows:,} records |
| `parquet/columns.json` | the row total |
| `raw/{run}/{csv}` | the CSV as served |

## Columns

| Column | Source column | Content |
|---|---|---|
| `time_axis_code` | 時間軸コード | text, the year with `100000` |
| `fiscal_year` | 年度 | integer, equal to the fiscal year (April to March) of `date` in all rows (checked) |
| `place` | 観察場所 | municipality and place name as written |
| `environment` | 環境区分 | {envs} |
| `longitude`, `latitude` | 経度, 緯度 | numbers |
| `date` | 目撃年月日 | date |
| `adults_text`, `juveniles_text`, `others_text` | 成獣(匹), 幼獣(匹), その他(匹) | text: numbers, and in `others_text` also `不明` ({unknown_n:,} rows) and, in {sentence_n} row, a sentence |
| `situation`, `individual_status`, `action` | 目撃時の状況, 個体の状況, その後の処置 | free text; null when empty |
| `municipality_code`, `municipality_code6`, `municipality` | 市町村コード, 市町村コード（6桁）, 市町村名 | the codes as text |
| `geometry` | | the point as WKB (longitude, latitude), WGS84 assumed |

## What was changed

- Column names and types: the source pads numbers with a trailing space (`135.251591 `); the padding
  was stripped from every field, and the dates, the year and the coordinates were typed. An empty
  field is null. Nothing else was changed (the Parquet was checked against the CSV with a second CSV
  reader, every row and column). Nothing was removed, merged or corrected.
- The source states no datum; WGS84 is assumed, and all points fall inside Kyoto Prefecture's
  bounding box with a margin (checked).

## Counts

| Fiscal year | Records |
|---|---|
{year_rows}

## Known issues

- FY2009 to FY2018 only; FY2018 is up to {last} (the catalogue's note on the yearly file says
  December). Newer Kyoto records are not in this catalogue entry.
- {dup_text}
- The counts of animals are text and have no total column; `others_text` has `不明` and one sentence
  that does not belong to a count (kept).
- {nl_n} fields hold line breaks (kept).
- The number of records per year varies by a factor of eight; the source does not say how the
  records were collected, and a sighting record is a report, not a census.

## Licence

The catalogue states Creative Commons Attribution 4.0 International (`cc-by-40-intl`) for the entry.
This dataset is offered under CC BY 4.0 and the credit is to Kyoto Prefecture:

> 出典：京都府「クマ目撃情報」（{page}）を加工して作成
"""


def main() -> int:
    run = sorted((ROOT / "data" / "raw").glob("*/MANIFEST.json"))[-1].parent
    m = json.loads((run / "MANIFEST.json").read_text())
    cols = json.loads((ROOT / "data/parquet/columns.json").read_text())
    assert cols["run"] == run.name
    d = pq.read_table(ROOT / "data/parquet/sighting.parquet").drop(["geometry"]).to_pydict()
    n = cols["rows"]
    yr = Counter(d["fiscal_year"])
    envs = ", ".join(
        f"{e} {c:,}" for e, c in Counter(x for x in d["environment"] if x).most_common()
    )
    place = Counter(zip(d["place"], d["latitude"], d["longitude"], strict=True)).most_common(1)[0]
    dup_n = sum(
        1
        for _, c in Counter(
            zip(d["place"], d["latitude"], d["longitude"], d["date"], strict=True)
        ).items()
        if c > 1
    )
    nl_n = sum(
        1
        for col in ("situation", "individual_status", "action", "place")
        for v in d[col]
        if v and "\n" in v
    )
    csv = k.CSV_RESOURCE
    f = m["files"][csv]
    card = CARD.format(
        repo=REPO, rows=n, page=k.PACKAGE_URL, title=m["title"], org=m["organization"],
        license_id=m["license_id"], meta_modified=m["metadata_modified"][:10], csv=csv,
        res_desc=(m["resource_description"] or "").strip().replace("\n", " "), csv_bytes=f["bytes"],
        run=run.name, fetched=run.name, res_modified=m["resource_last_modified"][:10],
        first=min(d["date"]), last=max(d["date"]), envs=envs,
        unknown_n=sum(v == "不明" for v in d["others_text"]),
        sentence_n=sum(1 for v in d["others_text"] if v and v not in ("不明",) and not v.isdigit()),
        year_rows="\n".join(f"| {y} | {yr[y]:,} |" for y in sorted(yr)),
        dup_text=(
            f"The most repeated place is 「{place[0][0]}」 ({place[1]:,} records at one coordinate); "
            f"{dup_n:,} groups of records share place, coordinates and date (kept)."
        ),
        nl_n=nl_n,
    )  # fmt: skip
    data = ROOT / "data"
    (data / "README.md").write_text(card, encoding="utf-8")
    (data / "LICENSE").write_text(
        "CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/legalcode)\n\n"
        "The records are from 京都府 クマ目撃情報, published in the BODIK open data catalogue under\n"
        f"Creative Commons Attribution 4.0 International ({k.PACKAGE_URL}), processed as described in README.md.\n"
        f"Credit: 出典：京都府「クマ目撃情報」（{k.PACKAGE_URL}）を加工して作成\n",
        encoding="utf-8",
    )
    (data / "provenance.yaml").write_text(
        f"source: 京都府 クマ目撃情報 (BODIK)\nurl: {k.PACKAGE_URL}\nlicense: {m['license_id']}\nrun: {run.name}\n"
        f"retrieved: {run.name}\nmetadata_modified: {m['metadata_modified']}\nrows: {n}\ncsv_sha256: {f['sha256']}\n",
        encoding="utf-8",
    )
    print("wrote data/README.md, LICENSE, provenance.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
