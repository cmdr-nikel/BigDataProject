# Group 16 — AniList Anime Catalogue on MongoDB
### Big Data Storage · Nova IMS · 2025/2026

---

## 1. Cover Page

**Project**: AniList Anime Catalogue — MongoDB Storage Solution
**Course**: Big Data Storage
**Academic year**: 2025/2026
**Group**: 16

| Name | Student Number |
|---|---|
| _<member 1>_ | _<number>_ |
| _<member 2>_ | _<number>_ |
| _<member 3>_ | _<number>_ |
| _<member 4>_ | _<number>_ |
| _<member 5>_ | _<number>_ |

**Submission date**: 22 May 2026

---

## 2. Company & Dataset (one-page description)

### The company

We model the back-end catalogue of **Otaku Stream** — a hypothetical
mid-tier anime streaming platform competing in the Western market with
Crunchyroll and HiDive. Otaku Stream's product team needs a flexible
catalogue store that lets editors (i) curate genre & decade rows on
the homepage, (ii) link titles to their production studios, characters
and user reviews, and (iii) measure engagement KPIs (popularity,
favourites, average score) across the catalogue.

### The dataset

We use the public **AniList GraphQL API** (`https://anilist.co`),
the second-largest anime tracking service after MyAnimeList. We
scraped the full anime endpoint plus related characters, staff,
studios, tags and reviews:

| Collection   |   Documents | Source endpoint |
|--------------|------------:|-----------------|
| `anime`      |     20 329 | `Page.media(type: ANIME)` |
| `characters` |    144 319 | nested `media.characters.edges.node` |
| `studios`    |     39 745 | nested `media.studios.edges.node` |
| `reviews`    |     13 629 | nested `media.reviews.nodes` |
| `tags`       |        418 | nested `media.tags`                  |
| **Total**    | **218 440** |                                      |

### Why MongoDB fits

The AniList data is **deeply nested, sparsely populated, and
heterogeneous**:

* Each anime carries optional one-to-many relationships
  (characters, staff, studios, reviews) whose cardinality varies from
  zero to several hundred.
* Many fields are nullable (~30 – 60 % null on several columns) and
  schema-evolving (e.g. `nextAiringEpisode` only exists for currently
  airing series).
* Some sub-objects are themselves polymorphic (the `coverImage`
  object varies by entry).

A document store handles this natively: every anime is one rich JSON
document; nested arrays stay as arrays; missing fields stay missing.
The same data in a relational schema would require ≥ 10 join tables,
many of which would be 80 %+ NULL.

---

## 3. Database Architecture

```
                        ┌───────────────┐
                        │  anime (20k)  │
                        ├───────────────┤
                        │ id            │
                        │ title{}       │
                        │ format        │
                        │ averageScore  │
                        │ popularity    │
                        │ genres[ ]     │
                        │ startDate{}   │
                        │ coverImage{}  │
                        │ stats_*{}     │
                        │               │
                        │ characters[id]│──┐
                        │ studios[id]   │──┼─► reference IDs
                        │ tags[id]      │──┤
                        │ reviews[id]   │──┘
                        └───────────────┘
                            │  │  │  │
       ┌────────────────────┘  │  │  └────────────────────────┐
       ▼                       ▼  ▼                           ▼
┌──────────────┐      ┌────────────┐    ┌──────────────┐  ┌──────────┐
│characters    │      │  studios   │    │    tags      │  │ reviews  │
│ (144k)       │      │  (40k)     │    │   (418)      │  │ (14k)    │
├──────────────┤      ├────────────┤    ├──────────────┤  ├──────────┤
│ id           │      │ id         │    │ id           │  │ id       │
│ name{}       │      │ name       │    │ name         │  │ summary  │
│ image{}      │      │ isAnimSt.. │    │ category     │  │ score    │
│ voiceActors[]│      │            │    │ description  │  │ rating   │
└──────────────┘      └────────────┘    └──────────────┘  └──────────┘
```

`anime` is the **hub document**. Heavy reusable entities
(characters, studios, tags, reviews) are stored as **separate
collections referenced by ID**, while small immutable nested
structures (title, dates, cover image, season stats) are
**embedded** inside the anime document.

This hybrid approach (embed vs reference) is the most important
design decision of the project — see Section 7.1.

---

## 4. Data Cleaning & ETL

Implemented in `Scripts/cleaning.ipynb`. Key steps:

1. **Column pruning** — 62 → 30 columns. Removed pandas artifacts,
   user-session flags, manga-only fields, redundant image variants,
   and AniList-internal editorial rankings.
2. **Type fixing** — 15 integer columns, 2 booleans, Unix timestamps
   to `datetime`. Pandas `Int64` (nullable) used so numeric NULLs
   survive the round-trip.
3. **Nested object reconstruction** — `startDate_year/month/day` →
   `startDate{}`, `title_romaji/english/native` → `title{}`,
   `trailer_*` → `trailer{}`, `coverImage_*` → `coverImage{}`.
4. **JSON parsing** — 16 stringified JSON columns parsed to Python
   objects with a defensive `safe_parse` helper.
5. **Sub-collection extraction** — characters, studios, tags, reviews
   pulled out of the nested arrays into their own collections, with
   IDs left behind in the anime document for $lookup.
6. **PyMongo import** — instead of `mongoimport` we use PyMongo
   directly with an oversize-document trim (see Section 7).

Output JSON files live in `Data/`, the load step lives in cell 26
of the notebook, and Section 5 of this report covers what we put on
top of it (validators + indexes).

---

## 5. Validation Rules (project requirement D)

Applied through `Scripts/setup_and_benchmark.py`. Full source also
mirrored in `schema_and_indexes.js.txt` for MongoSH. Total: **15+
distinct validation rules** across 3 collections.

### `anime` — 8 rules

| # | Field          | Rule                                                          |
|---|----------------|---------------------------------------------------------------|
| 1 | `id`           | required, `int` or `long`                                     |
| 2 | `title`        | required object containing at least `romaji`                  |
| 3 | `format`       | enum: TV, TV_SHORT, MOVIE, SPECIAL, OVA, ONA, MUSIC, null     |
| 4 | `averageScore` | numeric, between 0 and 100                                    |
| 5 | `episodes`     | numeric, ≥ 0                                                  |
| 6 | `popularity`   | numeric, ≥ 0                                                  |
| 7 | `status`       | enum: FINISHED, RELEASING, NOT_YET_RELEASED, CANCELLED, HIATUS|
| 8 | `isAdult`      | boolean                                                       |

### `studios` — 3 rules
- `id` required & numeric
- `name` string or null
- `isAnimationStudio` boolean

### `tags` — 4 rules
- `id` required & numeric
- `name` required string
- `category` string or null
- `isAdult` boolean

All validators are set with `validationLevel: "moderate"` and
`validationAction: "warn"` — see Design Decision 7.2.

---

## 6. Queries, Indexes & Aggregations

The full code lives in `Queries/group_16.txt`.
Performance numbers were measured by `Scripts/setup_and_benchmark.py`
on the local Compass-backed mongod instance.

### 6.1  Query performance — before vs after indexes (project F)

| Query                            | Stage before → after | Docs examined before → after | Time (ms) before → after | Speed-up |
|----------------------------------|----------------------|-----------------------------:|-------------------------:|---------:|
| Q1 — Top high-rated anime        | SORT → LIMIT         | 20 329 → 10                  | 37 → 2                   | 18.5×    |
| Q2 — Most popular anime          | SORT → LIMIT         | 20 329 → 10                  | 39 → 1                   | 39.0×    |
| Q3 — Anime by genre (Action)     | SORT → LIMIT         | 20 329 → 11                  | 42 → 2                   | 21.0×    |
| Q4 — Popular AND highly rated    | SORT → LIMIT         | 20 329 → 10                  | 44 → 0–1                 | > 40×    |
| Q5 — Recent anime (2020+)        | SORT → SORT          | 20 329 → 2 830               | 43 → 11                  | 3.9×     |

> Q5 still ends with a SORT stage because the index only orders by
> `seasonYear`; the secondary `popularity` sort is in-memory.
> Numbers in this table are taken from the latest report
> (`Reports/benchmark_report.md`); re-run the benchmark to refresh.

### 6.2  Indexes created

| Collection   | Index name           | Keys                                   | Notes      |
|--------------|----------------------|----------------------------------------|------------|
| `anime`      | `uniq_id`            | `{id: 1}`                              | unique     |
| `anime`      | `score_desc`         | `{averageScore: -1}`                   | Q1         |
| `anime`      | `popularity_desc`    | `{popularity: -1}`                     | Q2         |
| `anime`      | `genres_multikey`    | `{genres: 1}`                          | Q3, multikey on array |
| `anime`      | `season_year_desc`   | `{seasonYear: -1}`                     | Q5         |
| `anime`      | `score_pop_compound` | `{averageScore: -1, popularity: -1}`   | Q4 compound|
| `studios`    | `id_1`, `name_1`     | `{id: 1}` unique, `{name: 1}`          | A2         |
| `tags`       | `id_1`, `name_1`     | same                                   |            |
| `characters` | `id_1`               | `{id: 1}`                              |            |
| `reviews`    | `id_1`               | `{id: 1}` unique                       | A4         |

### 6.3  Aggregations (project G)

| ID  | Goal                                       | Stages | $lookup | Wall time |
|-----|--------------------------------------------|-------:|--------:|----------:|
| A1  | Quality trend by decade                    |   5    |   no    |  ~130 ms  |
| A2  | Top studios (production volume + quality)  |   9    |  yes    | ~5 900 ms |
| A3  | Genre engagement matrix                    |   5    |   no    |  ~110 ms  |
| A4  | Most-reviewed anime + avg user review score|   7    |  yes    |   ~70 ms  |

**Selected business insights** (full result tables in
`Reports/benchmark_report.md`):

- **A1**: Average user score has steadily risen from 43.3 (1940s) to
  64.1 (2020s) — the catalogue's overall quality, as perceived by
  users, increases monotonically over decades.
- **A2**: Toei Animation (821 titles), Sunrise (534) and Production
  I.G (422) dominate output volume; MADHOUSE (avg 66) and
  Production I.G (avg 66.1) lead on quality.
- **A3**: Comedy is the largest genre (6 778 titles), Drama has the
  highest avg score (66.2), Supernatural has the highest avg
  popularity (42 645) — useful for ad-targeting strategy.
- **A4**: Users who write full reviews give scores **5 – 10 points
  higher** than the platform-wide `averageScore`. Self-selection
  bias is real and should be considered in editorial recommendation
  scoring.

---

## 7. Design Decisions

This section answers the four "why" questions the project rubric
asks for.

### 7.1  Multiple collections vs one big document

**What we did**: split the data into 5 collections
(`anime`, `characters`, `studios`, `tags`, `reviews`).
The anime document keeps only **arrays of reference IDs** to the
sub-collections, plus the small immutable structures (`title`,
`startDate`, `coverImage`, etc.) embedded inline.

**Alternative we rejected**: keep everything embedded inside the
anime document.

| | Embedded everything | Hybrid (chosen) |
|---|---|---|
| Read latency for one anime page | 1 query, **best** | 1 query + N $lookup batches |
| Read latency for editorial dashboards | poor — must scan full nested arrays | **best** — small `anime` projection + bulk $lookup |
| Document size | Some anime > 16 MB → BSON limit **violated**, mongoimport fails | All anime < 1 MB on average |
| Storage of repeated entities | Same studio name stored 821 times | Studios stored once, referenced by ID |
| Write amplification on studio rename | rewrite every anime that uses it | update one studio document |
| Aggregation (e.g. genre × studio) | requires `$unwind` of giant arrays | clean `$unwind` + `$lookup` |

The single 16 MB BSON limit is what forced our hand: when we first
tried `mongoimport` of the fully-embedded `anime.json`, only the
first 3 documents loaded before mongoimport hit the limit. The
hybrid model fixed both the technical limit and the conceptual
duplication issue.

**Trade-off accepted**: queries that need full studio / character
detail now cost a join, but in our workload (catalogue browsing,
analytics) those joins are batched and indexed, so the latency cost
is sub-millisecond.

### 7.2  Validators: `moderate` + `warn` vs `strict` + `error`

**What we did**: every validator uses
`validationLevel: "moderate"` and `validationAction: "warn"`.

* **moderate** = inserts and *updates of valid documents* are
  checked; updates to documents that already violate the rule are
  not re-evaluated.
* **warn** = violations are written to the mongod log instead of
  rejected.

**Alternative we rejected**: `strict` + `error` (the textbook default).

| | strict + error | moderate + warn (chosen) |
|---|---|---|
| Behaviour on bad insert | INSERT FAILS, application sees an error | INSERT SUCCEEDS, mongod log records the violation |
| Suitable when… | Schema is fully known at design time | Schema is being discovered/cleaned iteratively |
| Risk of locking out existing data | Yes — applying a stricter validator can break operations on legacy docs | No — legacy docs are untouched until rewritten |
| Visibility of violations | Loud (application-level errors) | Quiet (need to read mongod logs) |

Our dataset has known sparse fields (e.g. `averageScore` is null for
20 % of records, `format` is null for 7 documents). With
`strict + error`, any bulk re-import or update during ETL would have
been rejected. With `moderate + warn` we capture the same guarantees
for *new* data — which is the platform's production traffic — while
keeping the historical dump intact. In a real production deployment
we would tighten to `strict + error` once a clean re-import has
been verified.

### 7.3  Studio "edge ID" data-quality quirk

**The bug**: the AniList GraphQL endpoint returns studios as edges
of the form

```json
{ "id": 5837421, "isMain": true,
  "node": { "id": 11, "name": "MADHOUSE",
            "isAnimationStudio": true } }
```

The *outer* `id` is the **edge instance id** (different for every
anime that lists MADHOUSE); the *inner* `node.id` is the **stable
studio entity id**. Our cleaning helper `unwrap_node()` merged these
two dicts with the outer overriding the inner — so we ended up
indexing studios by the edge id, producing **39 745 "studios"
documents for only 2 279 distinct studio names** (e.g.
"Toei Animation" appears 821 times with 821 different IDs).

**Decision**: rather than re-run the entire ~30-minute ETL we
worked around the issue inside aggregation A2:

* `$lookup` from `anime.studios[]` to `studios.id` (still works,
  because each edge id has its own doc with the right name).
* Then `$group` on `studio.name` instead of on `studio_id`.

This correctly consolidates the 821 MADHOUSE rows into a single
group of `animeCount: 386`. The technique is documented as a
"Data note" inside `group_16.txt` so future readers understand why
we group by name rather than by ID.

**Lesson learned**: when flattening GraphQL edge patterns, always
preserve the node's primary key. The fixed `unwrap_node` would be:

```python
def unwrap_node(item):
    if "node" not in item or not isinstance(item["node"], dict):
        return item
    outer = {k: v for k, v in item.items() if k not in ("node", "id")}
    return {**outer, **item["node"]}   # node values WIN
```

### 7.4  `$project` vs `$addFields` — the silent-null bug

**The bug**: an early version of aggregation A4 looked like

```js
{ $match:    { reviews: { $ne: null } } },
{ $project: { id: 1, title: 1, averageScore: 1,
              reviewCount: { $size: "$reviews" } } },
{ $sort:    { reviewCount: -1 } },
{ $limit:   10 },
{ $lookup:  { from: "reviews", localField: "reviews",
              foreignField: "id", as: "reviewDocs" } },
{ $addFields: { avgUserScore: { $avg: "$reviewDocs.score" } } }
```

The first `$project` keeps only the four listed fields, which
**drops the `reviews` array**. The downstream `$lookup` then has no
`localField` to match on, returns empty `reviewDocs[]` for every
document, and `$avg` of an empty array is `null` — so every row
came back with `avgUserScore: null` while no error was raised.

**Decision**: use `$addFields` (additive) instead of `$project`
(restrictive) until the very last stage:

```js
{ $match:     { reviews: { $ne: null } } },
{ $addFields: { reviewCount: { $size: "$reviews" } } },
{ $sort:      { reviewCount: -1 } },
{ $limit:     10 },
{ $lookup:    { ... } },
{ $addFields: { avgUserScore: { $avg: "$reviewDocs.score" } } },
{ $project:   { _id: 0, id: 1, title: 1, averageScore: 1,
                reviewCount: 1, avgUserScore: { $round: ["$avgUserScore", 1] } } }
```

**Lesson learned**: in MongoDB aggregations, **`$project` is
destructive** — anything not explicitly included is dropped. Always
prefer `$addFields` for intermediate computed fields, and reserve
`$project` for the final shaping stage. The bug was silent because
`$avg` on an empty array does not raise — it returns null — which
is exactly what an empty average should return semantically, so
there was no way for MongoDB to flag the upstream mistake.

---

## 8. Limitations & Future Work

* **Staff sub-collection not extracted.** `anime.staff` is still
  embedded; a handful of documents that listed > 50 staff entries
  had to be trimmed during PyMongo import. Splitting `staff` to its
  own collection would remove the trim entirely and unlock
  staff-centric analyses.
* **Reviews currently denormalised to integer IDs only.** Joining
  the full review text in A4 takes 70 ms today; with millions of
  reviews we would add `db.reviews.createIndex({ score: -1 })` and
  pre-aggregate per anime to a materialised view.
* **Studio dedup at ingestion time.** Fixing `unwrap_node()` and
  re-running ETL would let us drop the workaround in A2 and shrink
  the `studios` collection from 40 k to ~2.3 k documents.
* **No text search.** Adding a `$text` index on
  `title.romaji / english` plus `description` would let the
  platform's search bar work without a separate ElasticSearch.

---

## 9. Deliverables Map

| Project requirement | File(s) delivered |
|---|---|
| 1. Cover page                       | Section 1 of this document |
| 2. One-page description             | Section 2 of this document |
| 3. `group_16.bson` backup           | `Backup/group_16.zip` (folder of BSON + metadata, mongorestore-compatible) |
| 4. `group_16.txt` queries + agg.    | `Queries/group_16.txt`     |
| 5. Design-decisions report          | Sections 7 & 8 of this document |
| 6. PowerPoint                       | `Presentation/group_16.pptx` (TODO) |
| Auxiliary artefacts                 | `Scripts/cleaning.ipynb`, `Scripts/setup_and_benchmark.py`, `Scripts/backup_to_bson.py`, `schema_and_indexes.js.txt`, `Reports/benchmark_report.md` |

---

## 10. How to Reproduce

```powershell
# 1. Clean + load data (≈ 2 min)
jupyter notebook Scripts/cleaning.ipynb     # Run All

# 2. Apply validators, build indexes, benchmark queries,
#    run aggregations, write Reports/benchmark_report.md
python Scripts/setup_and_benchmark.py

# 3. Produce the deliverable BSON archive Backup/group_16.zip
python Scripts/backup_to_bson.py
```

To verify the backup on a fresh machine:

```powershell
Expand-Archive Backup/group_16.zip -DestinationPath .
mongorestore group_16/
```
