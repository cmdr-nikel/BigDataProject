"""
Produce a mongodump-compatible BSON backup of `anilist_db`.

Why a script and not `mongodump`?
    The MongoDB Database Tools (mongodump / mongorestore) are not
    bundled with Compass and are missing on most Anaconda Windows
    setups, so we replicate the dump format with PyMongo + bson.

Output structure (identical to `mongodump`):
    Backup/group_16/anilist_db/
        anime.bson           anime.metadata.json
        characters.bson      characters.metadata.json
        studios.bson         studios.metadata.json
        tags.bson            tags.metadata.json
        reviews.bson         reviews.metadata.json

The whole folder is then zipped to:
    Backup/group_16.zip
which is what you upload to Moodle.

To restore on any machine (the grader's machine) just unzip and:
    mongorestore Backup/group_16/
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

try:
    from pymongo import MongoClient
    import bson
except ImportError:
    import sys, subprocess as _sp
    _sp.check_call([sys.executable, "-m", "pip", "install", "pymongo"])
    from pymongo import MongoClient
    import bson


MONGO_URI    = "mongodb://localhost:27017"
DB_NAME      = "anilist_db"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR      = PROJECT_ROOT / "Backup" / "group_16" / DB_NAME
ZIP_PATH     = PROJECT_ROOT / "Backup" / "group_16"   # shutil adds .zip


def dump_collection(coll, out_dir: Path) -> tuple[int, int]:
    """Write `coll` to <out_dir>/<name>.bson + <name>.metadata.json.

    Returns (doc_count, bytes_written).
    """
    bson_path = out_dir / f"{coll.name}.bson"
    meta_path = out_dir / f"{coll.name}.metadata.json"

    # ---- 1. BSON file = concatenation of bson.encode(doc) ----
    count = 0
    with open(bson_path, "wb") as f:
        for doc in coll.find({}, no_cursor_timeout=True):
            f.write(bson.encode(doc))
            count += 1

    # ---- 2. metadata.json = format expected by mongorestore ----
    indexes_for_meta = []
    for idx in coll.list_indexes():
        clean = {k: v for k, v in idx.items() if k != "ns"}
        clean["ns"] = f"{DB_NAME}.{coll.name}"
        indexes_for_meta.append(clean)

    metadata = {
        "options":        {},
        "indexes":        indexes_for_meta,
        "uuid":           "",
        "collectionName": coll.name,
        "type":           "collection",
    }
    meta_path.write_text(
        json.dumps(metadata, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8",
    )

    return count, bson_path.stat().st_size


def main() -> None:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Dumping '{DB_NAME}' to {OUT_DIR}\n")
    total_docs = 0
    total_bytes = 0
    for name in db.list_collection_names():
        coll = db[name]
        n, sz = dump_collection(coll, OUT_DIR)
        total_docs  += n
        total_bytes += sz
        print(f"  {name:12s} {n:>7,} docs   {sz/1024/1024:>8.2f} MB")

    print(f"\nTotal: {total_docs:,} documents, {total_bytes/1024/1024:.2f} MB raw BSON.")

    # ---- 3. Zip the whole Backup/group_16/ folder ----
    backup_root = OUT_DIR.parent
    print(f"\nCreating zip archive at {ZIP_PATH}.zip ...")
    if ZIP_PATH.with_suffix(".zip").exists():
        ZIP_PATH.with_suffix(".zip").unlink()
    shutil.make_archive(str(ZIP_PATH), "zip", root_dir=backup_root.parent,
                        base_dir=backup_root.name)
    zip_size = ZIP_PATH.with_suffix(".zip").stat().st_size
    print(f"  zip size: {zip_size/1024/1024:.2f} MB")

    # ---- 4. Restore instructions ----
    print("\n" + "=" * 60)
    print("Restore instructions for the grader:")
    print("=" * 60)
    print("  1. Unzip group_16.zip")
    print("  2. Run:")
    print("        mongorestore group_16/")
    print("     (creates the 'anilist_db' database)")
    print(f"\n  Generated at: {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
