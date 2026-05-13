# Big Data Storage — Final Project
> Nova IMS · 2025/2026 · Group 16

---

## Dataset — AniList Anime Dataset

**Source:** [Kaggle — calebmwelsh/anilist-anime-dataset](https://www.kaggle.com/datasets/calebmwelsh/anilist-anime-dataset)  
**Origin:** AniList GraphQL API  
**Size:** ~20 000 anime titles · 43 fields after cleaning  
**Format:** CSV → cleaned JSON (ready for MongoDB import)

### Why MongoDB?
The dataset originates from a GraphQL API and contains deeply nested structures — `characters` with multilingual names and voice actors, `tags` with categories and descriptions, `studios`, `staff`, `relations` — that map naturally to MongoDB documents. A relational schema would require dozens of JOIN tables to represent the same data; here it lives as self-contained documents with embedded arrays and objects.

### Business Scenario
A streaming platform (think Netflix/Crunchyroll-like) uses this catalogue to power content discovery, editorial rankings, and analytics dashboards — tracking what genres trend by season, which studios produce the highest-rated content, and how user scores distribute across formats.

---

## Data Cleaning Pipeline — `Scripts/cleaning.ipynb`

The notebook takes the raw CSV and produces a MongoDB-ready JSON in 6 steps:

| Step | What happens |
|---|---|
| **1. Load** | Read `anilist_anime_data_complete.csv` (~20 k rows, 62 columns) |
| **2. Drop columns** | Remove pandas index, session flags, redundant image URLs, manga-only fields, external links (`siteUrl`, `externalLinks`), low-value metadata (`seasonInt`, `updatedAt`, `idMal`), and near-empty columns (`nextAiringEpisode` 99.9% null, `airingSchedule` 76.1% null) |
| **3. Fix types** | Cast to `Int64` (scores, counts), `bool`, `datetime`; reconstruct nested objects: `title`, `coverImage`, `trailer`, `startDate`, `endDate` |
| **4. Data quality** | Remove duplicates by `id`, drop rows with no `id`, clamp `averageScore`/`meanScore` to 0–100 |
| **5. Parse JSON columns** | 16 columns stored as JSON strings (e.g. `tags`, `characters`, `staff`) → parsed into Python lists/dicts |
| **6. Extract collections** | `characters`, `staff`, `studios`, `tags`, `reviews` extracted into separate collections; GraphQL `node` wrapper artifacts unwrapped into flat documents; `anime` documents retain ID reference lists only |
| **7. Save & import** | 6 JSON files written to `Data/`; `mongoimport` runs automatically for each collection with `--drop` to ensure idempotent re-runs |

Output: **20 329 `anime` documents · 36 fields** + 5 separate collections, auto-imported into MongoDB.

---

## Importing into MongoDB

### Automatic (recommended)

Import is automated — running `cleaning.ipynb` from top to bottom writes all 6 JSON files and calls `mongoimport` for each collection automatically. MongoDB must be running on `localhost:27017`. Each run uses `--drop`, so re-runs are safe and idempotent.

### Manual fallback

If auto-import fails, run from the project root:

```bash
mongoimport --db anilist_db --collection anime --file Data/anime.json --jsonArray --drop
mongoimport --db anilist_db --collection characters --file Data/characters.json --jsonArray --drop
mongoimport --db anilist_db --collection staff --file Data/staff.json --jsonArray --drop
mongoimport --db anilist_db --collection studios --file Data/studios.json --jsonArray --drop
mongoimport --db anilist_db --collection tags --file Data/tags.json --jsonArray --drop
mongoimport --db anilist_db --collection reviews --file Data/reviews.json --jsonArray --drop
```

If your MongoDB instance requires authentication, add `-u <user> -p <password> --authenticationDatabase admin` to each command.

---

## Collections Structure (≤ 10)

| Collection | Description |
|---|---|
| `anime` | Core documents — one per title, all basic fields; nested arrays replaced with ID reference lists |
| `characters` | Unique character profiles — names, images, roles; GraphQL `node` wrapper removed |
| `staff` | Directors, writers, composers — deduplicated across all anime |
| `studios` | Studio profiles — `isMain` flag preserved from GraphQL edge, `node` wrapper removed |
| `tags` | Tag taxonomy — categories, descriptions, spoiler flags |
| `reviews` | User reviews with ratings and summaries |

Relations between `anime` and the five collections are maintained via ID references, enabling `$lookup` aggregations.

---

## Project Checklist

### Phase 1 — Data Preparation
- [x] Dataset selected and justified
- [x] CSV loaded and inspected
- [x] Useless columns dropped
- [x] Data types fixed (Int64, bool, datetime, nested objects)
- [x] JSON columns parsed from strings → Python objects
- [x] Cleaned output saved as `anilist_cleaned.json`
- [x] Import into MongoDB (via `mongoimport` or Compass)

### Phase 2 — Validation Rules (≥ 5)
- [ ] `averageScore` — integer between 0 and 100
- [ ] `status` — enum: `FINISHED`, `RELEASING`, `NOT_YET_RELEASED`, `CANCELLED`, `HIATUS`
- [ ] `format` — enum: `TV`, `MOVIE`, `OVA`, `ONA`, `SPECIAL`, `TV_SHORT`, `MUSIC`
- [ ] `episodes` — integer > 0
- [ ] `id` — required, unique

### Phase 3 — Queries (≥ 5)
- [ ] Top 10 anime by average score per genre
- [ ] Most prolific studios by number of titles
- [ ] Score distribution by format (TV vs MOVIE vs OVA)
- [ ] Seasonal trends — average popularity by season/year
- [ ] Top countries of origin by total favourites

### Phase 4 — Indexes + Performance
- [ ] Run queries without indexes → capture `executionStats`
- [ ] Add indexes on frequent filter fields (`genres`, `averageScore`, `studios`, `status`)
- [ ] Re-run queries → compare execution time and documents scanned
- [ ] Document results in report

### Phase 5 — Aggregation Pipelines (≥ 3)
- [ ] Genre popularity over time (`$unwind` genres → `$group` by year)
- [ ] Studio leaderboard by average score (`$lookup` + `$group` + `$sort`)
- [ ] Score vs popularity correlation by format (`$group` + `$project`)

### Phase 6 — Report + Presentation
- [ ] Cover page
- [ ] 1-page company/dataset description
- [ ] Design decisions (collection structure, embedding vs referencing, index choices)
- [ ] PowerPoint slides
- [ ] `group_xxx.bson` backup
- [ ] `group_xxx.txt` with all queries and aggregations
- [ ] Zip everything → upload to Moodle (one member)

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
├── data/
│   ├── anilist_anime_data_complete.csv   # raw dataset
│   └── anilist_cleaned.json              # cleaned, MongoDB-ready
├── scripts/
│   ├── fetch_data.py                     # AniList API scraper
│   └── cleaning.py                       # data cleaning pipeline
├── queries/
│   └── group_xxx.txt                     # all queries & aggregations
├── report/
│   └── group_xxx_report.pdf
├── presentation/
│   └── group_xxx_slides.pptx
└── backup/
    └── group_xxx.bson
```

---

## Tools

- **MongoDB Compass** — recommended by professor, used for import and visual querying
- **MongoDB Atlas** — shared M0 free cluster for team collaboration
- **Python** — pandas + json for data cleaning (`cleaning.py`)
- **DataSpell / DataGrip** — JetBrains IDEs for notebooks and DB queries