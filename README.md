# kyoto-bear-sighting

Reproducible collection of the クマ目撃情報 (bear sightings, FY2009 to FY2018) of Kyoto Prefecture from
the BODIK open data catalogue. The dataset card is generated into `data/README.md` (not tracked; the
data is published at https://huggingface.co/datasets/yuiseki/kyoto-bear-sighting).

```
uv run python scripts/01_download.py      # the integrated CSV and the catalogue metadata (data/raw/<date>)
uv run python scripts/02_export_parquet.py
uv run python scripts/03_verify.py        # Parquet vs the CSV, with a second reader
uv run python scripts/04_card.py
uv run python src/publish.py [--push]     # dry run by default
```

Code: MIT. Data: CC BY 4.0, see the card.
