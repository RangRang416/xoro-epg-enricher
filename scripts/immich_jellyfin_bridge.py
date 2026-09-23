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


def immich_album_assets(album_name, api_key):
    r = requests.get(f"{IMMICH_URL}/api/albums", headers={"x-api-key": api_key}, timeout=30)
    r.raise_for_status()
    albums = {a["albumName"]: a["id"] for a in r.json()}
    if album_name not in albums:
        sys.exit(f"Album '{album_name}' nicht gefunden. Verfuegbar: {list(albums)}")
    r = requests.post(
        f"{IMMICH_URL}/api/search/metadata",
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        json={"albumIds": [albums[album_name]]},
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


def create_or_update_collection(name, jellyfin_ids, api_key):
    ids_param = ",".join(jellyfin_ids)
    existing = find_existing_collection(name, api_key)
    if existing:
        coll_id = existing["Id"]
        r = requests.post(
            f"{JELLYFIN_URL}/Collections/{coll_id}/Items",
            params={"Ids": ids_param, "api_key": api_key},
            timeout=30,
        )
        r.raise_for_status()
    else:
        r = requests.post(
            f"{JELLYFIN_URL}/Collections",
            params={"Name": name, "Ids": ids_param, "api_key": api_key},
            timeout=30,
        )
        r.raise_for_status()
        coll_id = r.json()["Id"]
    return coll_id


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("album_name", help="Exakter Immich-Albumname")
    parser.add_argument("--immich-key", default=os.environ.get("IMMICH_API_KEY"))
    parser.add_argument("--jellyfin-key", default=os.environ.get("JELLYFIN_API_KEY"))
    args = parser.parse_args()
    if not args.immich_key or not args.jellyfin_key:
        sys.exit("--immich-key/--jellyfin-key oder IMMICH_API_KEY/JELLYFIN_API_KEY erforderlich")

    assets = immich_album_assets(args.album_name, args.immich_key)
    matched, unmatched = match_assets_to_jellyfin(assets, args.jellyfin_key)
    if unmatched:
        print(f"WARNUNG: {len(unmatched)} Asset(s) nicht in Jellyfin gefunden: {unmatched}", file=sys.stderr)
    if not matched:
        sys.exit("Keine Treffer - Collection wird nicht angelegt/geaendert.")

    coll_id = create_or_update_collection(args.album_name, matched, args.jellyfin_key)
    print(f"Collection '{args.album_name}' ({coll_id}): {len(matched)} Items gesetzt, {len(unmatched)} nicht gematcht.")


if __name__ == "__main__":
    main()
