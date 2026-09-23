#!/usr/bin/env python3
"""Spiegelt ein einzelnes Immich-Album als Jellyfin-Collection (Pilot, #50).

Liest read-only per Immich-API die Asset-Liste eines Albums, matched jede
Datei über den gemeinsamen NAS-Pfad auf das entsprechende Jellyfin-Item und
legt/aktualisiert eine gleichnamige Jellyfin-Collection mit genau diesen
Items. Kein Cron/Automatismus - manueller Aufruf pro Album.

Usage:
    python3 immich_jellyfin_bridge.py "<Album-Name>" \
        --immich-key <key> --jellyfin-key <key>

API-Keys ausschließlich über --immich-key/--jellyfin-key oder die
Umgebungsvariablen IMMICH_API_KEY/JELLYFIN_API_KEY, nicht im Code.
"""
import argparse
import os
import sys

import requests

IMMICH_URL = os.environ.get("IMMICH_URL", "http://localhost:2283")
JELLYFIN_URL = os.environ.get("JELLYFIN_URL", "http://192.168.2.9:8096")

# Immich-externes Mount-Präfix -> Jellyfin-Library-ItemId (Komo-Freigabe)
LIBRARY_MAP = {
    "/usr/src/app/external/fotos/": "3287833bc027e2d73a0b50c58e48835b",
    "/usr/src/app/external/gifs/": "3bc5ba10a41a6caf1be0580137f2d3af",
    "/usr/src/app/external/filme/": "645bc3fdca0f5d6031b50cc8b4eb05e4",
}


def list_all_albums(api_key):
    r = requests.get(f"{IMMICH_URL}/api/albums", headers={"x-api-key": api_key}, timeout=30)
    r.raise_for_status()
    return {a["albumName"]: a["id"] for a in r.json() if a["albumName"] and a["assetCount"] > 0}


def album_assets(album_id, api_key):
    r = requests.post(
        f"{IMMICH_URL}/api/search/metadata",
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        json={"albumIds": [album_id]},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["assets"]["items"]


def jellyfin_items_by_filename(library_item_id, api_key):
    r = requests.get(
        f"{JELLYFIN_URL}/Items",
        params={"ParentId": library_item_id, "Recursive": "true", "Fields": "Path", "api_key": api_key},
        timeout=60,
    )
    r.raise_for_status()
    return {it["Path"].rsplit("/", 1)[-1]: it["Id"] for it in r.json()["Items"]}


def match_assets_to_jellyfin(assets, jellyfin_api_key):
    cache = {}
    matched, unmatched = [], []
    for asset in assets:
        path = asset["originalPath"]
        prefix = next((p for p in LIBRARY_MAP if path.startswith(p)), None)
        if prefix is None:
            unmatched.append(path)
            continue
        lib_id = LIBRARY_MAP[prefix]
        if lib_id not in cache:
            cache[lib_id] = jellyfin_items_by_filename(lib_id, jellyfin_api_key)
        filename = path.rsplit("/", 1)[-1]
        jf_id = cache[lib_id].get(filename)
        (matched if jf_id else unmatched).append(jf_id or path)
    return matched, unmatched


def find_existing_collection(name, api_key):
    r = requests.get(
        f"{JELLYFIN_URL}/Items",
        params={"searchTerm": name, "IncludeItemTypes": "BoxSet", "Recursive": "true", "api_key": api_key},
        timeout=30,
    )
    r.raise_for_status()
    return next((it for it in r.json()["Items"] if it["Name"] == name), None)


CHUNK_SIZE = 40  # vermeidet HTTP 414 (URI Too Long) bei grossen Alben


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def create_or_update_collection(name, jellyfin_ids, api_key):
    chunks = list(chunked(jellyfin_ids, CHUNK_SIZE))
    existing = find_existing_collection(name, api_key)
    if existing:
        coll_id = existing["Id"]
        rest = chunks
    else:
        r = requests.post(
            f"{JELLYFIN_URL}/Collections",
            params={"Name": name, "Ids": ",".join(chunks[0]), "api_key": api_key},
            timeout=30,
        )
        r.raise_for_status()
        coll_id = r.json()["Id"]
        rest = chunks[1:]

    for chunk in rest:
        r = requests.post(
            f"{JELLYFIN_URL}/Collections/{coll_id}/Items",
            params={"Ids": ",".join(chunk), "api_key": api_key},
            timeout=30,
        )
        r.raise_for_status()
    return coll_id


def sync_one(album_name, album_id, jellyfin_key):
    assets = album_assets(album_id, IMMICH_KEY_HOLDER["key"])
    matched, unmatched = match_assets_to_jellyfin(assets, jellyfin_key)
    if unmatched:
        print(f"  WARNUNG: {len(unmatched)} Asset(s) nicht in Jellyfin gefunden: {unmatched}", file=sys.stderr)
    if not matched:
        print(f"  '{album_name}': keine Treffer, Collection wird nicht angelegt/geaendert.")
        return
    coll_id = create_or_update_collection(album_name, matched, jellyfin_key)
    print(f"  '{album_name}' ({coll_id}): {len(matched)} Items gesetzt, {len(unmatched)} nicht gematcht.")


IMMICH_KEY_HOLDER = {"key": None}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("album_name", nargs="?", help="Exakter Immich-Albumname (weglassen = --all)")
    parser.add_argument("--all", action="store_true", help="Alle vorhandenen Alben synchronisieren")
    parser.add_argument("--immich-key", default=os.environ.get("IMMICH_API_KEY"))
    parser.add_argument("--jellyfin-key", default=os.environ.get("JELLYFIN_API_KEY"))
    args = parser.parse_args()
    if not args.immich_key or not args.jellyfin_key:
        sys.exit("--immich-key/--jellyfin-key oder IMMICH_API_KEY/JELLYFIN_API_KEY erforderlich")
    if not args.album_name and not args.all:
        sys.exit("Entweder einen Albumnamen angeben oder --all fuer alle Alben.")

    IMMICH_KEY_HOLDER["key"] = args.immich_key
    albums = list_all_albums(args.immich_key)

    if args.all:
        print(f"Synchronisiere {len(albums)} Album(e): {list(albums)}")
        for name, album_id in albums.items():
            sync_one(name, album_id, args.jellyfin_key)
    else:
        if args.album_name not in albums:
            sys.exit(f"Album '{args.album_name}' nicht gefunden. Verfuegbar: {list(albums)}")
        sync_one(args.album_name, albums[args.album_name], args.jellyfin_key)


if __name__ == "__main__":
    main()
