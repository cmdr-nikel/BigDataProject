# Big Data Storage — Final Project
> Nova IMS · 2025/2026 · Group 16

---

## Dataset — AniList Anime Dataset

**Source:** [Kaggle — calebmwelsh/anilist-anime-dataset](https://www.kaggle.com/datasets/calebmwelsh/anilist-anime-dataset)
**Origin:** AniList GraphQL API
**Size:** 20 329 anime + 144 319 characters + 39 745 studios + 13 629 reviews + 418 tags (**218 440 documents total**)
**Format:** CSV → cleaned JSON → 5 MongoDB collections

### Why MongoDB?
The dataset originates from a GraphQL API and contains deeply nested structures — `characters` with multilingual names and voice actors, `tags` with categories and descriptions, `studios`, `staff`, `relations` — that map naturally to MongoDB documents. A relational schema would require dozens of JOIN tables to represent the same data; here it lives as self-contained documents with embedded objects and ID references to sibling collections.

### Business Scenario
A streaming platform (think Netflix/Crunchyroll-like, modelled in the report as **"Otaku Stream"**) uses this catalogue to power content discovery, editorial rankings, and analytics dashboards — tracking what genres trend by decade, which studios produce the highest-rated content, and how user scores distribute across formats.

---

## Data Cleaning Pipeline — `Scripts/cleaning.ipynb`

The notebook takes the raw CSV and produces MongoDB-ready data in 7 steps:

| Step | What happens |
|---|---|
| **1. Load** | Read `anilist_anime_data_complete.csv` (20 329 rows, 62 columns) |
| **2. Drop columns** | Remove pandas index, session flags, redundant image URLs, manga-only fields, external links (`siteUrl`, `externalLinks`), low-value metadata (`seasonInt`, `updatedAt`, `idMal`), and near-empty columns (`nextAiringEpisode` 99.9 % null, `airingSchedule` 76.1 % null) — 62 → 39 columns |
| **3. Fix types** | Cast to `Int64` (scores, counts), `bool`, `datetime`; reconstruct nested objects: `title`, `coverImage`, `trailer`, `startDate`, `endDate` |
| **4. Data quality** | Remove duplicates by `id`, drop rows with no `id`, clamp `averageScore` to 0–100 |
| **5. Parse JSON columns** | 16 columns stored as JSON strings (e.g. `tags`, `characters`, `staff`) → parsed into Python lists/dicts |
| **6. Extract collections** | `characters`, `studios`, `tags`, `reviews` extracted into separate collections; GraphQL `node` wrapper artifacts unwrapped into flat documents; `anime` documents retain ID reference lists only |
| **7. Save & import** | 5 JSON files written to `Data/`; imported via **PyMongo** (not `mongoimport`) so we can auto-trim documents that would exceed the 16 MB BSON limit |

Output: **20 329 `anime` documents · 30 fields** + 4 referenced collections, all auto-imported into MongoDB.

---

## Importing into MongoDB

### Automatic (recommended)

Import is automated — running `cleaning.ipynb` from top to bottom writes all 5 JSON files and inserts each collection via PyMongo. MongoDB must be running on `localhost:27017`. Each run uses `.drop()` first, so re-runs are safe and idempotent.

### Why PyMongo instead of `mongoimport`?
* `mongoimport` is **not bundled** with Compass or the default Anaconda installation, so it is missing on most team machines.
* Even when available, `mongoimport` **aborts at the first document that exceeds the 16 MB BSON limit** (we hit this — see `Scripts/cleaning.ipynb` cell 26 for the fix). The PyMongo importer auto-trims the offending `staff` / `relations` / `description` fields and continues.

### Manual fallback (if `mongoimport` is on your PATH)
```bash
mongoimport --db anilist_db --collection anime      --file Data/anime.json      --jsonArray --drop
mongoimport --db anilist_db --collection characters --file Data/characters.json --jsonArray --drop
mongoimport --db anilist_db --collection studios    --file Data/studios.json    --jsonArray --drop
mongoimport --db anilist_db --collection tags       --file Data/tags.json       --jsonArray --drop
mongoimport --db anilist_db --collection reviews    --file Data/reviews.json    --jsonArray --drop
```

---

## Collections Structure (5 ≤ 10)

| Collection | Documents | Description |
|---|---:|---|
| `anime` | 20 329 | Core documents — one per title; nested arrays replaced with ID reference lists. `staff`, `genres`, `relations`, `stats_*`, `startDate`, `coverImage` and `title` stay **embedded** because they are small and immutable |
| `characters` | 144 319 | Character profiles — names, images, roles; GraphQL `node` wrapper removed |
| `studios` | 39 745 | Studio profiles — `isMain` flag preserved from GraphQL edge, `node` wrapper removed (see Design Decision 7.3 in the report for a known edge-ID data-quality issue) |
| `tags` | 418 | Tag taxonomy — categories, descriptions, spoiler flags |
| `reviews` | 13 629 | User reviews with ratings and summaries |

Relations between `anime` and the four reference collections are maintained via ID arrays, enabling `$lookup` aggregations.

> **Note**: the original plan included a separate `staff` collection (would have been 6 collections). We left `staff` embedded inside `anime` because the extraction was non-trivial and the existing structure already satisfies the project requirements. See `Reports/group_16_report.md` §8 for the rationale and how to extend.

---

## Project Checklist

### Phase 1 — Data Preparation
- [x] Dataset selected and justified
- [x] CSV loaded and inspected
- [x] Useless columns dropped (62 → 30)
- [x] Data types fixed (`Int64`, `bool`, `datetime`, nested objects)
- [x] JSON columns parsed from strings → Python objects
- [x] Cleaned output saved as 5 per-collection JSON files in `Data/`
- [x] Imported into MongoDB (via PyMongo, with oversize-doc auto-trim)

### Phase 2 — Validation Rules (≥ 5 → **15** delivered)
- [x] `anime.id` — required, integer or long
- [x] `anime.title` — required nested object with `romaji`
- [x] `anime.format` — enum: `TV`, `TV_SHORT`, `MOVIE`, `SPECIAL`, `OVA`, `ONA`, `MUSIC`
- [x] `anime.averageScore` — integer/long between 0 and 100
- [x] `anime.episodes` — integer/long ≥ 0
- [x] `anime.popularity` — integer/long ≥ 0
- [x] `anime.status` — enum: `FINISHED`, `RELEASING`, `NOT_YET_RELEASED`, `CANCELLED`, `HIATUS`
- [x] `anime.isAdult` — boolean
- [x] `studios.id` — required integer
- [x] `studios.name` — string or null
- [x] `studios.isAnimationStudio` — boolean
- [x] `tags.id` — required integer
- [x] `tags.name` — required string
- [x] `tags.category` — string or null
- [x] `tags.isAdult` — boolean
- [x] Implementation: `Scripts/setup_and_benchmark.py` (via PyMongo) **and** `schema_and_indexes.js.txt` (MongoSH version)

### Phase 3 — Queries (≥ 5 → **5** delivered, in `Queries/group_16.txt`)
- [x] **Q1** — Top high-rated anime (`averageScore ≥ 85`)
- [x] **Q2** — Most popular anime (`popularity ≥ 100 000`)
- [x] **Q3** — Anime by genre (Action, multikey index demo)
- [x] **Q4** — Popular AND highly rated (compound-index demo)
- [x] **Q5** — Recent anime releases (`seasonYear ≥ 2020`)

### Phase 4 — Indexes + Performance
- [x] Baseline benchmark — every query run as COLLSCAN over 20 329 docs
- [x] 6 indexes built on `anime` (`uniq_id`, `score_desc`, `popularity_desc`, `genres_multikey`, `season_year_desc`, `score_pop_compound`) + reference-collection indexes
- [x] After-index benchmark — IXSCAN, ≤ 12 keys examined for Q1-Q4
- [x] Results documented in `Reports/benchmark_report.md` and report §6 — typical speed-ups **18× – 40×**

### Phase 5 — Aggregation Pipelines (≥ 3 → **4** delivered)
- [x] **A1** — Catalogue quality trend by decade (5 stages, `$addFields` + `$group`)
- [x] **A2** — Top studios by output + quality (9 stages, **`$lookup` join**)
- [x] **A3** — Genre engagement matrix (5 stages, `$unwind` + `$group`)
- [x] **A4** — Most-reviewed anime + avg user review score (7 stages, **`$lookup` join**)

### Phase 6 — Report + Presentation
- [x] Cover page — `Reports/group_16_report.md` §1 (fill in member names)
- [x] 1-page company / dataset description — §2
- [x] Design decisions (4 deep-dive decisions, embed-vs-reference, validator strategy, edge-ID quirk, `$project` vs `$addFields` lesson) — §7
- [x] `group_16.txt` with all queries + aggregations — `Queries/group_16.txt`
- [x] `group_16.bson` backup — `Backup/group_16.zip` (mongodump-compatible folder, restored with `mongorestore`)
- [ ] PowerPoint slides — _outline in `Presentation/group_16_outline.md`, slides to be authored_
- [ ] Zip everything → upload to Moodle (one member submits)

---

## Deadlines

| Event | Date |
|---|---|
| Submission (Moodle) | **May 22, 23:59** |
| Presentation | TBD — book slot via course link |

> Late penalty: −1 point per day, up to −5

---

## Team

| Name | Student No. | Role |
|---|---|---|
| — | — | Data cleaning & pipeline |
| — | — | Validation rules & indexes |
| — | — | Queries |
| — | — | Aggregation pipelines |
| — | — | Report & presentation |

---

## Repository Structure

```
/
├── README.md
├── Big_Data_Storage_Project.md                # project brief from teacher
├── schema_and_indexes.js.txt                  # MongoSH-flavoured schema + indexes
├── Data/                                      # raw CSV + 5 cleaned JSON files
│   ├── anilist_anime_data_complete.csv
│   ├── anilist_anime_data_complete.pkl
│   ├── anilist_anime_data_complete.xlsx
│   ├── anime.json                             # 20 329 docs
│   ├── characters.json                        # 144 319 docs
│   ├── studios.json                           # 39 745 docs
│   ├── tags.json                              # 418 docs
│   ├── reviews.json                           # 13 629 docs
│   └── fetch_data.py                          # AniList GraphQL scraper
├── Scripts/
│   ├── cleaning.ipynb                         # CSV → JSON → MongoDB (PyMongo)
│   ├── setup_and_benchmark.py                 # validators + indexes + query/agg benchmark → benchmark_report.md
│   └── backup_to_bson.py                      # mongodump-compatible BSON archive
├── Queries/
│   └── group_16.txt                           # ALL queries + ALL aggregations (deliverable #4)
├── Reports/
│   ├── group_16_report.md                     # main deliverable — 10 sections, design decisions (deliverable #5)
│   └── benchmark_report.md                    # auto-generated index-impact tables + aggregation outputs
├── Backup/
│   └── group_16.zip                           # mongorestore-compatible backup (deliverable #3)
└── Presentation/
    └── group_16_outline.md                    # 10-min talk outline (to be filled with .pptx)
```

---

## How to Reproduce (any machine with MongoDB on localhost:27017)

```powershell
# 1. Clean + load data into MongoDB (≈ 2 min)
jupyter notebook Scripts/cleaning.ipynb           # Run All

# 2. Apply validators, build indexes, benchmark queries, run aggregations
python Scripts/setup_and_benchmark.py             # writes Reports/benchmark_report.md

# 3. Produce the deliverable BSON archive
python Scripts/backup_to_bson.py                  # writes Backup/group_16.zip
```

To verify the backup on a fresh machine:

```powershell
Expand-Archive Backup/group_16.zip -DestinationPath .
mongorestore group_16/
```

---

## Tools

- **MongoDB Compass** — recommended by professor, used for visual querying and the MongoSH tab
- **PyMongo** — used for ETL, validators, indexes, query benchmarks and BSON backup (avoids the missing-`mongoimport` problem)
- **Python** (pandas + json + bson) — data cleaning, schema scripting, and reporting
- **Jupyter Notebook** — `cleaning.ipynb` orchestrates the full ETL
