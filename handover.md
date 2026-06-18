# Handover — xoro-epg-enricher (2026-06-18)

## Status: WI-1 bis WI-5 abgeschlossen

## Repo
https://github.com/RangRang416/xoro-epg-enricher

## Was diese Session gemacht hat

### WI-2 (Spike)
- Befund: `movie.nfo` wird von Jellyfin für Episode-Items ignoriert → `{basename}.nfo` nötig
- TypeOptions Episode-Eintrag war bereits gesetzt ✓

### WI-1 (enricher.py)
- `TVDb.episode_overview()`: deutsche Episode-Overview via v4 API, EN-Fallback
- `build_episode_nfo`: Fallback-Kette episode_overview → epg_title → series.overview
- `move_recording` Serien-Branch: `Show/Season NN/` + pro-Datei-Move + NFO-Rename
- Commit: a732038

### WI-3 (migrate_series.py)
- 11 Enricher-Flat-Folder nach `Show/Season NN/` migriert, 0 Fehler
- Alle Typ-B-Ordner (bestehende Serien) unberührt
- Commit: 5d0cf91, Fix: 0428490

### WI-4 (Diagnose)
- #22-Crash: Client-seitiger NPE im Android TV nach stale Item-IDs (Post-Migration)
- Server meldet `Guid can't be empty` bei `/Items/{stale-id}` → kein Server-Fix nötig
- Löst sich nach vollständigem Library-Scan + App-Neustart

### WI-5 (Hardening)
- `EnableRealtimeMonitor=false` in Serien/options.xml (war 8192 inotify-Limit erschöpft)
- `AutomaticRefreshIntervalDays=0` bestätigt ✓
- Einzige Refresh-Quelle: enricher-seitiger `POST /Library/Refresh`

## NAS-Zustand nach dieser Session
- `/volume1/dvb-library/enricher.py` — WI-1 deployed
- `/volume1/dvb-library/migrate_series.py` — WI-3 deployed (kann bei Bedarf nochmals laufen)
- `/volume1/1/Serien/` — Flat-Folder migriert → Show/Season NN/ Struktur
- Jellyfin läuft Library-Scan (kann ~10-20 Min dauern bei 1GB RAM)
- Jellyfin wird nach Scan Restart benötigen damit options.xml-Änderung (RealtimeMonitor=false) wirkt

## Jellyfin-Neustart nach Scan
Wenn Scan abgeschlossen: Container neu starten damit RealtimeMonitor-Änderung aktiv wird.
```
ssh synology
/usr/local/bin/docker restart jellyfin
```

## Nächste Schritte
- Issues #21/#22/#23 können nach Jellyfin-Scan + Restart als gelöst markiert werden
- Neu aufgenommene Serien werden ab jetzt korrekt in Show/Season NN/ abgelegt
- **Neu beobachtet (2026-06-18):** Breaking Bad (Typ-B) hat keine Episodenbeschreibungen → Enricher hat Typ-B nicht verarbeitet → neues Issue
- Keine deutschen Serienbeschreibungen / keine Episoden-Poster → separate Issues nächste Session
- Phase VI (VI-1 Gate: Transcode-Diagnose) danach
