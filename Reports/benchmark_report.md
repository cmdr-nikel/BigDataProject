# Benchmark Report — `anilist_db`
_Group 16 · Big Data Storage · Nova IMS · auto-generated_

## 1. Collection sizes
| Collection | Documents |
|---|---:|
| anime | 20,329 |
| characters | 144,319 |
| studios | 39,745 |
| tags | 418 |
| reviews | 13,629 |

## 2. Validators applied
Applied `$jsonSchema` validators on the 3 most-structured collections:
- **anime**: 8 rules (id, title.romaji, format enum, averageScore 0-100, episodes ≥ 0, popularity ≥ 0, status enum, isAdult bool)
- **studios**: 3 rules (id, name, isAnimationStudio)
- **tags**: 4 rules (id, name, category, isAdult)

_validationLevel: moderate, validationAction: warn — chosen so legacy documents are not rejected, only logged._

## 3. Query performance — before vs after indexes
| Query | Stage (before → after) | Docs examined (before → after) | Time ms (before → after) | Speed-up |
|---|---|---:|---:|---:|
| Q1 — Top high-rated anime | SORT → LIMIT | 20,329 → 10 | 37 → 2 | 18.5× |
| Q2 — Most popular anime | SORT → LIMIT | 20,329 → 10 | 39 → 1 | 39.0× |
| Q3 — Anime by genre (Action) | SORT → LIMIT | 20,329 → 11 | 42 → 2 | 21.0× |
| Q4 — Popular AND highly rated | SORT → LIMIT | 20,329 → 10 | 44 → 0 | — |
| Q5 — Recent anime (2020+) | SORT → SORT | 20,329 → 2,830 | 43 → 11 | 3.9× |

## 4. Indexes created

### `anime`
- `_id_` → {_id:1}
- `uniq_id` → {id:1} (unique)
- `score_desc` → {averageScore:-1}
- `popularity_desc` → {popularity:-1}
- `genres_multikey` → {genres:1}
- `season_year_desc` → {seasonYear:-1}
- `score_pop_compound` → {averageScore:-1, popularity:-1}

### `studios`
- `_id_` → {_id:1}
- `id_1` → {id:1} (unique)
- `name_1` → {name:1}

### `tags`
- `_id_` → {_id:1}
- `id_1` → {id:1} (unique)
- `name_1` → {name:1}

### `characters`
- `_id_` → {_id:1}
- `id_1` → {id:1}

### `reviews`
- `_id_` → {_id:1}
- `id_1` → {id:1} (unique)

## 5. Aggregations

### A1 — Catalogue quality trend by decade
- Stages: 5
- Rows returned: 9
- Wall time: 180 ms

First 10 results:

```json
[
  {
    "animeCount": 25,
    "topScore": 53,
    "decade": 1940.0,
    "avgScore": 43.3,
    "avgPopularity": 580.0
  },
  {
    "animeCount": 36,
    "topScore": 57,
    "decade": 1950.0,
    "avgScore": 43.8,
    "avgPopularity": 478.0
  },
  {
    "animeCount": 172,
    "topScore": 69,
    "decade": 1960.0,
    "avgScore": 48.5,
    "avgPopularity": 838.0
  },
  {
    "animeCount": 336,
    "topScore": 81,
    "decade": 1970.0,
    "avgScore": 54.9,
    "avgPopularity": 1923.0
  },
  {
    "animeCount": 1003,
    "topScore": 88,
    "decade": 1980.0,
    "avgScore": 55.9,
    "avgPopularity": 3855.0
  },
  {
    "animeCount": 1586,
    "topScore": 87,
    "decade": 1990.0,
    "avgScore": 57.0,
    "avgPopularity": 6190.0
  },
  {
    "animeCount": 3293,
    "topScore": 90,
    "decade": 2000.0,
    "avgScore": 58.4,
    "avgPopularity": 11653.0
  },
  {
    "animeCount": 5926,
    "topScore": 90,
    "decade": 2010.0,
    "avgScore": 60.3,
    "avgPopularity": 24640.0
  },
  {
    "animeCount": 3774,
    "topScore": 91,
    "decade": 2020.0,
    "avgScore": 64.1,
    "avgPopularity": 23316.0
  }
]
```

### A2 — Top studios (uses $lookup)
- Stages: 9
- Rows returned: 15
- Wall time: 5878 ms

First 10 results:

```json
[
  {
    "animeCount": 821,
    "totalPopularity": 7378420,
    "studioName": "Toei Animation",
    "avgScore": 62.5
  },
  {
    "animeCount": 534,
    "totalPopularity": 6620505,
    "studioName": "Sunrise",
    "avgScore": 65.3
  },
  {
    "animeCount": 422,
    "totalPopularity": 16447797,
    "studioName": "Production I.G",
    "avgScore": 66.1
  },
  {
    "animeCount": 411,
    "totalPopularity": 14049955,
    "studioName": "J.C.STAFF",
    "avgScore": 64.6
  },
  {
    "animeCount": 386,
    "totalPopularity": 14903633,
    "studioName": "MADHOUSE",
    "avgScore": 66.0
  },
  {
    "animeCount": 358,
    "totalPopularity": 7826902,
    "studioName": "TMS Entertainment",
    "avgScore": 65.8
  },
  {
    "animeCount": 309,
    "totalPopularity": 6225817,
    "studioName": "Studio DEEN",
    "avgScore": 64.9
  },
  {
    "animeCount": 300,
    "totalPopularity": 10687196,
    "studioName": "Studio Pierrot",
    "avgScore": 65.2
  },
  {
    "animeCount": 287,
    "totalPopularity": 4396842,
    "studioName": "OLM",
    "avgScore": 62.9
  },
  {
    "animeCount": 264,
    "totalPopularity": 520292,
    "studioName": "Pink Pineapple",
    "avgScore": 58.0
  }
]
```

### A3 — Genre engagement matrix
- Stages: 5
- Rows returned: 19
- Wall time: 111 ms

First 10 results:

```json
[
  {
    "animeCount": 6778,
    "totalFavourites": 3222694,
    "genre": "Comedy",
    "avgScore": 62.0,
    "avgPopularity": 19054.0
  },
  {
    "animeCount": 5006,
    "totalFavourites": 4103015,
    "genre": "Action",
    "avgScore": 63.8,
    "avgPopularity": 28213.0
  },
  {
    "animeCount": 4489,
    "totalFavourites": 2860582,
    "genre": "Fantasy",
    "avgScore": 62.6,
    "avgPopularity": 22273.0
  },
  {
    "animeCount": 3745,
    "totalFavourites": 2462687,
    "genre": "Adventure",
    "avgScore": 63.0,
    "avgPopularity": 21134.0
  },
  {
    "animeCount": 3175,
    "totalFavourites": 4202851,
    "genre": "Drama",
    "avgScore": 66.2,
    "avgPopularity": 37155.0
  },
  {
    "animeCount": 2900,
    "totalFavourites": 1300899,
    "genre": "Sci-Fi",
    "avgScore": 62.1,
    "avgPopularity": 17165.0
  },
  {
    "animeCount": 2708,
    "totalFavourites": 1835395,
    "genre": "Slice of Life",
    "avgScore": 64.5,
    "avgPopularity": 24571.0
  },
  {
    "animeCount": 2621,
    "totalFavourites": 2160742,
    "genre": "Romance",
    "avgScore": 64.4,
    "avgPopularity": 32268.0
  },
  {
    "animeCount": 1768,
    "totalFavourites": 2239530,
    "genre": "Supernatural",
    "avgScore": 65.3,
    "avgPopularity": 42645.0
  },
  {
    "animeCount": 1605,
    "totalFavourites": 77520,
    "genre": "Hentai",
    "avgScore": 54.8,
    "avgPopularity": 1876.0
  }
]
```

### A4 — Most-reviewed anime + avg user score (uses $lookup)
- Stages: 7
- Rows returned: 10
- Wall time: 72 ms

First 10 results:

```json
[
  {
    "id": 1,
    "averageScore": 86,
    "title": {
      "romaji": "Cowboy Bebop",
      "english": "Cowboy Bebop",
      "native": "カウボーイビバップ"
    },
    "reviewCount": 25,
    "avgUserScore": 89.7
  },
  {
    "id": 32,
    "averageScore": 85,
    "title": {
      "romaji": "Shin Seiki Evangelion Movie: Air / Magokoro wo, Kimi ni",
      "english": "Neon Genesis Evangelion: The End of Evangelion",
      "native": "新世紀エヴァンゲリオン劇場版 Air/まごころを、君に"
    },
    "reviewCount": 25,
    "avgUserScore": 84.6
  },
  {
    "id": 19,
    "averageScore": 88,
    "title": {
      "romaji": "MONSTER",
      "english": "Monster",
      "native": "MONSTER"
    },
    "reviewCount": 25,
    "avgUserScore": 80.4
  },
  {
    "id": 21,
    "averageScore": 87,
    "title": {
      "romaji": "ONE PIECE",
      "english": "ONE PIECE",
      "native": "ONE PIECE"
    },
    "reviewCount": 25,
    "avgUserScore": 92.5
  },
  {
    "id": 227,
    "averageScore": 79,
    "title": {
      "romaji": "FLCL",
      "english": "FLCL",
      "native": "フリクリ"
    },
    "reviewCount": 25,
    "avgUserScore": 93.9
  },
  {
    "id": 437,
    "averageScore": 85,
    "title": {
      "romaji": "PERFECT BLUE",
      "english": "Perfect Blue",
      "native": "PERFECT BLUE"
    },
    "reviewCount": 25,
    "avgUserScore": 91.4
  },
  {
    "id": 1575,
    "averageScore": 85,
    "title": {
      "romaji": "Code Geass: Hangyaku no Lelouch",
      "english": "Code Geass: Lelouch of the Rebellion",
      "native": "コードギアス 反逆のルルーシュ"
    },
    "reviewCount": 25,
    "avgUserScore": 80.8
  },
  {
    "id": 1535,
    "averageScore": 84,
    "title": {
      "romaji": "DEATH NOTE",
      "english": "Death Note",
      "native": "DEATH NOTE"
    },
    "reviewCount": 25,
    "avgUserScore": 84.4
  },
  {
    "id": 339,
    "averageScore": 80,
    "title": {
      "romaji": "serial experiments lain",
      "english": "Serial Experiments Lain",
      "native": "serial experiments lain"
    },
    "reviewCount": 25,
    "avgUserScore": 87.1
  },
  {
    "id": 30,
    "averageScore": 83,
    "title": {
      "romaji": "Shin Seiki Evangelion",
      "english": "Neon Genesis Evangelion",
      "native": "新世紀エヴァンゲリオン"
    },
    "reviewCount": 25,
    "avgUserScore": 80.6
  }
]
```
