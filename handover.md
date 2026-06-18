# Handover — xoro-epg-enricher (2026-06-18)

## Status: WI-1 deployed, WI-3 als nächstes

## Repo
https://github.com/RangRang416/xoro-epg-enricher

## Was diese Session gemacht hat
- WI-2 Spike abgeschlossen: `movie.nfo` war Ursache (Jellyfin ignoriert für Episode-Items)
- WI-1 implementiert + getestet (6/6 AK) + deployed (Commit a732038)
  - `TVDb.episode_overview()` mit DE-Fallback
  - `build_episode_nfo` Fallback-Kette
  - `move_recording` → `Show/Season NN/{basename}.*`
  - NFO-Sidecar-Name == Video-Basename

## NAS-Zustand
- `/volume1/dvb-library/enricher.py` — aktuell (WI-1 deployed)
- Bestehende Serien in `/volume1/1/Serien/` liegen noch im alten Flat-Folder-Format
- Jellyfin TypeOptions: Episode-Eintrag vorhanden ✓

## Nächste Schritte
1. **WI-3** — Migration bestehender Flat-Folder: dry-run auf `/volume1/1/Serien/`, dann live
2. **WI-4** — #22-Diagnose: HTTP-500-Stacktrace bei POST /Sessions/Playing/Stopped
3. **WI-5** — Hardening: inotify-Limit + AutomaticRefreshIntervalDays

## Reihenfolge Work Items
WI-3 → WI-4 → WI-5
