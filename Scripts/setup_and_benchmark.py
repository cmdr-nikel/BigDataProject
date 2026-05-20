"""
AniList MongoDB — one-shot setup & benchmark script
====================================================
Group 16  •  Big Data Storage  •  Nova IMS 2025/2026

What this script does (in order):
  1. Drops all user-defined indexes on `anime` → baseline
  2. Runs every query in group_16.txt with COLLSCAN and records
     executionTimeMillis / docs examined
  3. Applies the JSON-schema validators (D in the project brief)
  4. Creates all indexes (F in the project brief)
  5. Re-runs every query — now with IXSCAN — and records the same
     metrics, so you get a clean before/after comparison
  6. Runs the 4 aggregations (G in the project brief)
  7. Writes everything to Reports/benchmark_report.md

Run from anywhere:
    python Scripts/setup_and_benchmark.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

try:
    from pymongo import MongoClient
    from bson.son import SON
except ImportError:
    import subprocess as _sp, sys
    _sp.check_call([sys.executable, "-m", "pip", "install", "pymongo"])
    from pymongo import MongoClient
    from bson.son import SON


# --------------------------------------------------------------------- #
#  Config
# --------------------------------------------------------------------- #
MONGO_URI    = "mongodb://localhost:27017"
DB_NAME      = "anilist_db"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH  = PROJECT_ROOT / "Reports" / "benchmark_report.md"


# --------------------------------------------------------------------- #
#  Validators (8 rules on anime + 4 rules on studios + 4 on tags = 16)
# --------------------------------------------------------------------- #
VALIDATORS = {
    "anime": {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["id", "title", "format"],
                "properties": {
                    "id": {
                        "bsonType": ["int", "long"],
                        "description": "AniList ID — required integer",
                    },
                    "title": {
                        "bsonType": "object",
                        "required": ["romaji"],
                        "properties": {
                            "romaji":  {"bsonType": ["string", "null"]},
                            "english": {"bsonType": ["string", "null"]},
                            "native":  {"bsonType": ["string", "null"]},
                        },
                    },
                    "format": {
                        "enum": ["TV", "TV_SHORT", "MOVIE", "SPECIAL",
                                 "OVA", "ONA", "MUSIC", None],
                    },
                    "averageScore": {
                        "bsonType": ["int", "long", "null"],
                        "minimum": 0, "maximum": 100,
                    },
                    "episodes":   {"bsonType": ["int", "long", "null"], "minimum": 0},
                    "popularity": {"bsonType": ["int", "long", "null"], "minimum": 0},
                    "status": {
                        "enum": ["FINISHED", "RELEASING", "NOT_YET_RELEASED",
                                 "CANCELLED", "HIATUS", None],
                    },
                    "isAdult": {"bsonType": ["bool", "null"]},
                },
            }
        },
        "validationLevel":  "moderate",
        "validationAction": "warn",
    },
    "studios": {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["id"],
                "properties": {
                    "id":                {"bsonType": ["int", "long"]},
                    "name":              {"bsonType": ["string", "null"]},
                    "isAnimationStudio": {"bsonType": ["bool", "null"]},
                },
            }
        },
        "validationLevel":  "moderate",
        "validationAction": "warn",
    },
    "tags": {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["id", "name"],
                "properties": {
                    "id":       {"bsonType": ["int", "long"]},
                    "name":     {"bsonType": "string"},
                    "category": {"bsonType": ["string", "null"]},
                    "isAdult":  {"bsonType": ["bool", "null"]},
                },
            }
        },
        "validationLevel":  "moderate",
        "validationAction": "warn",
    },
}


# --------------------------------------------------------------------- #
#  Indexes
# --------------------------------------------------------------------- #
INDEX_SPECS = {
    "anime": [
        ([("id", 1)],                                {"unique": True, "name": "uniq_id"}),
        ([("averageScore", -1)],                     {"name": "score_desc"}),
        ([("popularity", -1)],                       {"name": "popularity_desc"}),
        ([("genres", 1)],                            {"name": "genres_multikey"}),
        ([("seasonYear", -1)],                       {"name": "season_year_desc"}),
        ([("averageScore", -1), ("popularity", -1)], {"name": "score_pop_compound"}),
    ],
    "studios":    [([("id", 1)], {"unique": True}), ([("name", 1)], {})],
    "tags":       [([("id", 1)], {"unique": True}), ([("name", 1)], {})],
    "characters": [([("id", 1)], {})],
    "reviews":    [([("id", 1)], {"unique": True})],
}


# --------------------------------------------------------------------- #
#  Queries (mirror group_16.txt)
# --------------------------------------------------------------------- #
QUERIES = [
    {
        "name":   "Q1 — Top high-rated anime",
        "filter": {"averageScore": {"$gte": 85}},
        "sort":   [("averageScore", -1)],
        "limit":  10,
    },
    {
        "name":   "Q2 — Most popular anime",
        "filter": {"popularity": {"$gte": 100000}},
        "sort":   [("popularity", -1)],
        "limit":  10,
    },
    {
        "name":   "Q3 — Anime by genre (Action)",
        "filter": {"genres": "Action"},
        "sort":   [("popularity", -1)],
        "limit":  10,
    },
    {
        "name":   "Q4 — Popular AND highly rated",
        "filter": {"averageScore": {"$gte": 80}, "popularity": {"$gte": 100000}},
        "sort":   [("averageScore", -1), ("popularity", -1)],
        "limit":  10,
    },
    {
        "name":   "Q5 — Recent anime (2020+)",
        "filter": {"seasonYear": {"$gte": 2020}},
        "sort":   [("seasonYear", -1), ("popularity", -1)],
        "limit":  20,
    },
]


# --------------------------------------------------------------------- #
#  Aggregations (mirror group_16.txt)
# --------------------------------------------------------------------- #
AGGREGATIONS = [
    {
        "name": "A1 — Catalogue quality trend by decade",
        "pipeline": [
            {"$match": {"startDate.year": {"$ne": None}, "averageScore": {"$ne": None}}},
            {"$addFields": {"decade": {"$multiply": [
                {"$floor": {"$divide": ["$startDate.year", 10]}}, 10
            ]}}},
            {"$group": {
                "_id": "$decade",
                "animeCount":    {"$sum": 1},
                "avgScore":      {"$avg": "$averageScore"},
                "avgPopularity": {"$avg": "$popularity"},
                "topScore":      {"$max": "$averageScore"},
            }},
            {"$project": {
                "_id": 0,
                "decade":        "$_id",
                "animeCount":    1,
                "avgScore":      {"$round": ["$avgScore", 1]},
                "avgPopularity": {"$round": ["$avgPopularity", 0]},
                "topScore":      1,
            }},
            {"$sort": {"decade": 1}},
        ],
    },
    {
        "name": "A2 — Top studios (uses $lookup)",
        "pipeline": [
            {"$match":  {"studios": {"$ne": None}}},
            {"$unwind": "$studios"},
            {"$lookup": {
                "from": "studios", "localField": "studios",
                "foreignField": "id", "as": "studio",
            }},
            {"$unwind": "$studio"},
            {"$match":  {
                "studio.isAnimationStudio": True,
                "studio.name": {"$ne": None},
            }},
            {"$group": {
                "_id":             "$studio.name",
                "animeCount":      {"$sum": 1},
                "avgScore":        {"$avg": "$averageScore"},
                "totalPopularity": {"$sum": "$popularity"},
            }},
            {"$project": {
                "_id": 0,
                "studioName":      "$_id",
                "animeCount":      1,
                "avgScore":        {"$round": ["$avgScore", 1]},
                "totalPopularity": 1,
            }},
            {"$sort":  {"animeCount": -1}},
            {"$limit": 15},
        ],
    },
    {
        "name": "A3 — Genre engagement matrix",
        "pipeline": [
            {"$match":  {"genres": {"$ne": None, "$not": {"$size": 0}}}},
            {"$unwind": "$genres"},
            {"$group": {
                "_id":             "$genres",
                "animeCount":      {"$sum": 1},
                "avgScore":        {"$avg": "$averageScore"},
                "avgPopularity":   {"$avg": "$popularity"},
                "totalFavourites": {"$sum": "$favourites"},
            }},
            {"$project": {
                "_id": 0,
                "genre":           "$_id",
                "animeCount":      1,
                "avgScore":        {"$round": ["$avgScore", 1]},
                "avgPopularity":   {"$round": ["$avgPopularity", 0]},
                "totalFavourites": 1,
            }},
            {"$sort": {"animeCount": -1}},
        ],
    },
    {
        "name": "A4 — Most-reviewed anime + avg user score (uses $lookup)",
        "pipeline": [
            {"$match": {"reviews": {"$ne": None}}},
            {"$addFields": {"reviewCount": {"$size": "$reviews"}}},
            {"$sort":  {"reviewCount": -1}},
            {"$limit": 10},
            {"$lookup": {
                "from": "reviews", "localField": "reviews",
                "foreignField": "id", "as": "reviewDocs",
            }},
            {"$addFields": {"avgUserScore": {"$avg": "$reviewDocs.score"}}},
            {"$project": {
                "_id": 0,
                "id": 1, "title": 1, "averageScore": 1, "reviewCount": 1,
                "avgUserScore": {"$round": ["$avgUserScore", 1]},
            }},
        ],
    },
]


# --------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------- #
def drop_user_indexes(coll):
    for idx in list(coll.list_indexes()):
        if idx["name"] != "_id_":
            coll.drop_index(idx["name"])


def benchmark_query(db, coll_name, q):
    """Run query under explain(executionStats) and return key metrics."""
    cmd = SON([
        ("explain", SON([
            ("find",   coll_name),
            ("filter", q["filter"]),
            ("sort",   SON(q["sort"])),
            ("limit",  q["limit"]),
        ])),
        ("verbosity", "executionStats"),
    ])
    result = db.command(cmd)
    stats  = result.get("executionStats", {})
    plan   = result.get("queryPlanner", {}).get("winningPlan", {})

    def walk_stage(p):
        s = p.get("stage")
        if s:
            return s
        for k in ("inputStage", "innerStage"):
            if k in p:
                return walk_stage(p[k])
        return None

    return {
        "stage":               walk_stage(plan),
        "totalDocsExamined":   stats.get("totalDocsExamined"),
        "totalKeysExamined":   stats.get("totalKeysExamined"),
        "nReturned":           stats.get("nReturned"),
        "executionTimeMillis": stats.get("executionTimeMillis"),
    }


def apply_validators(db):
    for coll_name, spec in VALIDATORS.items():
        db.command({"collMod": coll_name, **spec})


def create_indexes(db):
    for coll_name, specs in INDEX_SPECS.items():
        for keys, opts in specs:
            db[coll_name].create_index(keys, **opts)


# --------------------------------------------------------------------- #
#  Main
# --------------------------------------------------------------------- #
def main():
    client = MongoClient(MONGO_URI)
    db     = client[DB_NAME]

    lines = []
    p     = lines.append

    p("# Benchmark Report — `anilist_db`\n")
    p("_Group 16 · Big Data Storage · Nova IMS · auto-generated_\n\n")

    # ---------- 1. counts ----------
    p("## 1. Collection sizes\n")
    p("| Collection | Documents |\n|---|---:|\n")
    for c in ["anime", "characters", "studios", "tags", "reviews"]:
        p(f"| {c} | {db[c].count_documents({}):,} |\n")

    # ---------- 2. drop indexes & baseline benchmark ----------
    print("Dropping user indexes on 'anime' for baseline benchmark...")
    drop_user_indexes(db.anime)

    print("Benchmarking queries WITHOUT indexes (COLLSCAN baseline)...")
    before = {}
    for q in QUERIES:
        before[q["name"]] = benchmark_query(db, "anime", q)
        print(f"  {q['name']}: {before[q['name']]}")

    # ---------- 3. validators ----------
    print("\nApplying JSON-schema validators...")
    apply_validators(db)
    p("\n## 2. Validators applied\n")
    p("Applied `$jsonSchema` validators on the 3 most-structured collections:\n")
    p("- **anime**: 8 rules (id, title.romaji, format enum, averageScore 0-100, "
      "episodes ≥ 0, popularity ≥ 0, status enum, isAdult bool)\n")
    p("- **studios**: 3 rules (id, name, isAnimationStudio)\n")
    p("- **tags**: 4 rules (id, name, category, isAdult)\n")
    p("\n_validationLevel: moderate, validationAction: warn — chosen so legacy "
      "documents are not rejected, only logged._\n")

    # ---------- 4. create indexes & after benchmark ----------
    print("\nCreating indexes on all collections...")
    create_indexes(db)

    print("Benchmarking queries WITH indexes (IXSCAN)...")
    after = {}
    for q in QUERIES:
        after[q["name"]] = benchmark_query(db, "anime", q)
        print(f"  {q['name']}: {after[q['name']]}")

    # ---------- 5. comparison table ----------
    p("\n## 3. Query performance — before vs after indexes\n")
    p("| Query | Stage (before → after) | Docs examined (before → after) | "
      "Time ms (before → after) | Speed-up |\n")
    p("|---|---|---:|---:|---:|\n")
    for q in QUERIES:
        b, a = before[q["name"]], after[q["name"]]
        bt = b["executionTimeMillis"] or 0
        at = a["executionTimeMillis"] or 0
        speedup = f"{bt / at:.1f}×" if at else "—"
        p(f"| {q['name']} | {b['stage']} → {a['stage']} | "
          f"{b['totalDocsExamined']:,} → {a['totalDocsExamined']:,} | "
          f"{bt} → {at} | {speedup} |\n")

    # ---------- 6. indexes listed ----------
    p("\n## 4. Indexes created\n\n")
    for coll in ["anime", "studios", "tags", "characters", "reviews"]:
        p(f"### `{coll}`\n")
        for idx in db[coll].list_indexes():
            keys = ", ".join(f"{k}:{v}" for k, v in idx["key"].items())
            extra = " (unique)" if idx.get("unique") else ""
            p(f"- `{idx['name']}` → {{{keys}}}{extra}\n")
        p("\n")

    # ---------- 7. aggregations ----------
    p("## 5. Aggregations\n")
    for agg in AGGREGATIONS:
        print(f"\nRunning {agg['name']}...")
        t0 = time.perf_counter()
        results = list(db.anime.aggregate(agg["pipeline"]))
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        print(f"  {len(results)} rows in {elapsed_ms} ms")

        p(f"\n### {agg['name']}\n")
        p(f"- Stages: {len(agg['pipeline'])}\n")
        p(f"- Rows returned: {len(results)}\n")
        p(f"- Wall time: {elapsed_ms} ms\n\n")
        p("First 10 results:\n\n```json\n")
        p(json.dumps(results[:10], indent=2, default=str, ensure_ascii=False))
        p("\n```\n")

    # ---------- 8. write ----------
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text("".join(lines), encoding="utf-8")
    print(f"\nReport written to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
