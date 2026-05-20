# PowerPoint Outline — Group 16
### Big Data Storage · Nova IMS · 2025/2026
### Target length: **10 minutes** · **12 slides** (≈ 50 sec per slide on average)

---

## Speaker assignment (suggested)

| Slides | Section            | Speaker     |
|--------|--------------------|-------------|
| 1–2    | Intro & Agenda     | _Member 1_  |
| 3–4    | Dataset & MongoDB  | _Member 2_  |
| 5–6    | Architecture & ETL | _Member 3_  |
| 7–9    | Validation, queries & aggregations | _Member 4_  |
| 10–11  | Design decisions & demo | _Member 5_ |
| 12     | Q&A                | All         |

> Total speech budget per slide is intentionally short — aim for one
> idea per slide, no walls of text. Keep bullets ≤ 5 per slide and
> ≤ 8 words per bullet. Numbers and diagrams sell faster than prose.

---

## Slide 1 — Title (15 s)

**Layout**: full-bleed background (anime collage or AniList screenshot blurred).
**On screen**:
- **Big Data Storage — AniList Anime Catalogue on MongoDB**
- Group 16 · Nova IMS · 2025/2026
- 5 member names

**Speak**:
- "Good afternoon. We're Group 16, and our project models an anime
  streaming platform's catalogue on MongoDB using the AniList
  GraphQL dataset."

---

## Slide 2 — Agenda (20 s)

**On screen** (5 numbered bullets):
1. The company and the dataset
2. Architecture — 5 collections
3. ETL & data quality
4. Validation, queries, indexes, aggregations
5. Design decisions + lessons learned

**Speak**:
- "Here's where we're going — quick context, then the technical core,
  then the four design decisions we want to defend."

---

## Slide 3 — Company & Dataset (60 s)

**Layout**: 2 columns. **Left** = company; **right** = dataset stats.

**Left column — "Otaku Stream"**:
- Mid-tier anime streaming platform
- Competes with Crunchyroll, HiDive
- Needs: editorial curation + analytics + recommendations

**Right column — dataset**:
- Source: AniList public GraphQL API
- **218 440 documents across 5 collections**
- 20 329 anime · 144 k characters · 40 k studios · 14 k reviews · 418 tags

**Speak**:
- "We modelled the catalogue back-end of a Crunchyroll-like service.
  The data comes from AniList, a public GraphQL API — over 200 000
  documents in total, distributed across five collections."

---

## Slide 4 — Why MongoDB (60 s)

**On screen** (table or 3 vertical "cards"):

| Trait of the data         | What MongoDB gives us |
|---------------------------|-----------------------|
| Deeply nested objects     | Native JSON documents |
| 30–60 % null on many cols | Schema-less, no NULL columns |
| Polymorphic sub-objects   | Per-document schema   |
| Many-to-many (anime↔studios) | `$lookup` joins on demand |

**Visual**: small SQL-vs-Mongo schema comparison (a relational version
would need ~10 join tables; Mongo needs 5 collections).

**Speak**:
- "Why MongoDB? The same dataset in PostgreSQL would need around ten
  join tables, most of them sparse. As JSON documents, every anime
  is one self-contained record. Nulls disappear, polymorphism is
  free, and joins become explicit aggregation stages."

---

## Slide 5 — Database Architecture (60 s)

**Layout**: the ER-style diagram from `Reports/group_16_report.md` §3.

**Highlight on screen**:
- `anime` is the **hub** document
- Heavy entities (characters, studios, tags, reviews) → **separate
  collections referenced by ID**
- Small immutable structures (title, dates, cover image) → **embedded**

**Speak**:
- "We chose a hybrid model — small immutable structures embedded,
  heavy reusable entities referenced by ID. This is Design
  Decision #1, and we'll come back to it on slide 10."

---

## Slide 6 — ETL Pipeline (60 s)

**Layout**: horizontal flow with 7 boxes.

```
CSV → drop cols → fix types → quality → parse JSON → extract → import
62 cols                                              5 colls   PyMongo
                                                              (auto-trim)
```

**Highlights on screen**:
- 62 → 30 columns
- 16 JSON-string columns parsed
- **PyMongo importer** (not `mongoimport`) — auto-trims docs that
  would exceed the 16 MB BSON limit
- One Jupyter notebook = full pipeline, idempotent

**Speak**:
- "Cleaning is a single Jupyter notebook. The most interesting step
  is the import — `mongoimport` aborted at 3 of 20 329 anime
  because one document exceeded the 16 MB BSON limit. We wrote a
  PyMongo importer that auto-trims and inserts in batches."

---

## Slide 7 — Validation Rules (45 s)

**Layout**: 3 grouped boxes, one per collection.

| `anime` (8) | `studios` (3) | `tags` (4) |
|---|---|---|
| id required int    | id required    | id required  |
| title.romaji req.  | name string    | name string  |
| format enum (7)    | isAnimSt. bool | category str |
| averageScore 0-100 |                | isAdult bool |
| episodes ≥ 0       |                |              |
| popularity ≥ 0     |                |              |
| status enum (5)    |                |              |
| isAdult bool       |                |              |

**Bottom-right note**: `validationLevel: moderate · validationAction: warn`

**Speak**:
- "15 validation rules across three collections — well above the
  required minimum of 5. We chose `moderate + warn` rather than
  `strict + error`; that's Design Decision #2, on slide 10."

---

## Slide 8 — Queries + Index Speed-Up (90 s) ★

**Layout**: full-width performance table (this is the headline slide).

| Query                          | Before (ms) | After (ms) | Speed-up |
|--------------------------------|------------:|-----------:|---------:|
| Q1 — Top high-rated            | 37          | 2          | **18×**  |
| Q2 — Most popular              | 39          | 1          | **39×**  |
| Q3 — By genre (multikey idx)   | 42          | 2          | **21×**  |
| Q4 — Popular + highly rated    | 44          | 0–1        | **> 40×**|
| Q5 — Recent releases           | 43          | 11         | 3.9×     |

**Below table**: 6 indexes built: `uniq_id`, `score_desc`,
`popularity_desc`, `genres_multikey`, `season_year_desc`,
`score_pop_compound`.

**Speak**:
- "Five queries, all benchmarked with `executionStats` before and
  after indexing. The numbers speak for themselves — between 4× and
  40× speed-up. Q4 is the most satisfying: the compound index on
  `(averageScore, popularity)` serves both the filter and the sort,
  so the plan goes straight from `LIMIT` to `IXSCAN` with no SORT
  stage at all."

---

## Slide 9 — Aggregations & Business Insights (90 s) ★

**Layout**: 4 quadrants, one per aggregation. Each quadrant shows
**one chart or one big number**.

- **A1 — Quality trend by decade**
  - 1940s avg = **43.3** → 2020s avg = **64.1**
  - Big number + sparkline

- **A2 — Top studios by output** (uses `$lookup`)
  - Toei Animation 821 · Sunrise 534 · Production I.G 422 · MADHOUSE 386
  - Bar chart

- **A3 — Genre engagement matrix**
  - Comedy biggest (6 778), Drama best score (66.2), Supernatural most popular (42 k)
  - Mini scatter or table

- **A4 — Reviewers score higher** (uses `$lookup`)
  - Avg user-review score **5–10 points higher** than platform `averageScore`
  - Side-by-side bars for Cowboy Bebop / ONE PIECE / FLCL

**Speak**:
- "Four aggregations, two of which use `$lookup` to join across
  collections. Best business insight: users who write full reviews
  systematically rate 5 to 10 points higher than the platform
  average — that's a self-selection bias worth correcting for in
  the recommendation engine."

---

## Slide 10 — Design Decisions (90 s) ★★

**Layout**: 4 quadrants, each titled by the decision.

- **DD-1 · Embed vs Reference**
  - Hybrid model. Embedded ones stayed embedded. Heavy reusable ones referenced.
  - Forcing reason: 16 MB BSON cap

- **DD-2 · Validator strategy**
  - `moderate + warn` instead of `strict + error`
  - Lets legacy nulls survive while still policing new writes

- **DD-3 · Studio "edge-ID" quirk**
  - 39 745 IDs but only 2 279 unique names
  - Workaround: `$lookup` then `$group by name`

- **DD-4 · `$project` vs `$addFields`**
  - `$project` is destructive — dropped the `reviews` field used by the next `$lookup`
  - Lesson: keep computed columns additive until the final stage

**Speak**:
- "Four design decisions defended in the report. The most painful
  one is #4 — `$project` silently dropped a field that the next
  `$lookup` needed, and `$avg` on an empty array returns null, so
  the bug never raised an exception. Lesson: prefer `$addFields`
  until the very last stage."

---

## Slide 11 — Live Demo (60 s)

**Show in Compass**:
1. Connect to `mongodb://localhost:27017` → `anilist_db`
2. Open `anime` collection → highlight nested `title`, `coverImage`, `studios[]`
3. Switch to **Indexes** tab → show 6 indexes
4. Switch to **MongoSH** tab → paste **Q4** with `.explain("executionStats")` → highlight `executionTimeMillis = 0`
5. Paste **A2** → show MADHOUSE, Toei, Sunrise on top

**Speak**:
- "Quick live demo in Compass. Here's the `anime` collection, here
  are the six indexes, and here's Q4 returning in zero milliseconds
  thanks to the compound index."

---

## Slide 12 — Thank-you / Q&A (15 s)

**On screen**:
- "Thanks for listening — questions?"
- Repo / submission folder name
- Five member names again
- (small) deliverable file map:
  - `group_16_report.pdf`
  - `group_16.txt`
  - `group_16.bson` (in `group_16.zip`)
  - `group_16.pptx`

---

## Timing Cheat-sheet

| # | Slide                                  | Target | Cumulative |
|---|----------------------------------------|-------:|-----------:|
| 1 | Title                                  | 0:15   | 0:15       |
| 2 | Agenda                                 | 0:20   | 0:35       |
| 3 | Company & Dataset                      | 1:00   | 1:35       |
| 4 | Why MongoDB                            | 1:00   | 2:35       |
| 5 | Architecture                           | 1:00   | 3:35       |
| 6 | ETL pipeline                           | 1:00   | 4:35       |
| 7 | Validation rules                       | 0:45   | 5:20       |
| 8 | Queries + index speed-up ★             | 1:30   | 6:50       |
| 9 | Aggregations + insights ★              | 1:30   | 8:20       |
| 10 | Design decisions ★★                    | 1:30   | 9:50       |
| 11 | Live demo                              | 1:00   | 10:50 ⚠   |
| 12 | Thanks / Q&A                           | 0:15   | 11:05 ⚠   |

> **If running long**, cut the **demo (slide 11)** down to 30 s — just
> show indexes and one explain output. The technical content of the
> demo is already on slides 8 and 9, so the demo is optional dressing.

---

## Visual style guidelines

- One **bold key statistic** per slide (e.g. "**18 -- 40× speed-up**",
  "**218 440 documents**", "**0 ms after index**").
- Colour: lean on AniList's brand blue (#02A9FF) + a single accent.
- All code in monospace; **never** show more than ~6 lines of code
  on a slide — for longer pipelines, show a diagram instead.
- Use icons (e.g. database, magnifying glass, gear) rather than
  clip-art screenshots.

---

## Slide-to-Report cross-reference

| Slide | Report section |
|---|---|
| 3  | §2 (company / dataset)            |
| 4  | §2 (why MongoDB)                  |
| 5  | §3 (architecture)                 |
| 6  | §4 (ETL)                          |
| 7  | §5 (validators)                   |
| 8  | §6.1, §6.2 + `benchmark_report.md` §3 |
| 9  | §6.3 + `benchmark_report.md` §5   |
| 10 | §7.1–§7.4 (design decisions)      |
| 11 | live in Compass                   |
