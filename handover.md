# Handover — xoro-epg-enricher (2026-06-17)

## Status: Issues #21/#22/#23 geplant, WI-2-Spike abgebrochen

## Repo
https://github.com/RangRang416/xoro-epg-enricher

## Was diese Session gemacht hat
- Issues #21/#22/#23 analysiert (Jellyfin + Synology direkt befragt)
- Planner gespawnt (2× revidiert, Controller-Freigabe), Pläne als GitHub-Kommentare hinterlegt
- projekt.md aktualisiert (Abschnitt Issues #21/#22/#23 ergänzt)
- WI-2-Spike gestartet: TypeOptions Episode-Eintrag in Jellyfin API gesetzt (HTTP 204 ✓) — aber NFO-Reader springt trotzdem nicht an

## Jellyfin-Zustand (nach dieser Session)
- Serien-Library TypeOptions: **Episode-Eintrag ist jetzt vorhanden** (zusätzlich zu Series)
  - `{"Type": "Episode", "MetadataFetchers": [], ..., "LocalMetadataReaderOrder": ["Nfo"]}`
  - `EnableInternetProviders: false` — unverändert
- Kein laufender Prozess, Jellyfin idle

## Offenes Problem: WI-2 (Jellyfin NFO-Reader)
TypeOptions-Hypothese hat **nicht** funktioniert. Breaking Bad Episoden zeigen weiterhin "Episode 1" ohne Overview, auch nach FullRefresh mit ReplaceAllMetadata=true.
Mögliche Ursachen (ungeklärt):
- `LocalMetadataReaderOrder` in TypeOptions ist kein gültiges Feld (nur auf Library-Root-Ebene valide)
- Item-Refresh liest keine lokalen Dateien neu — Library-Scan nötig
- Jellyfin-Bug oder Konfiguration tiefer vergraben (z.B. in XML-Config-Dateien auf Synology)

## Nächste Schritte
1. **WI-2 neu angehen** — einfacher Ansatz: `POST /Library/Refresh` (vollständiger Library-Scan statt Item-Refresh) und prüfen ob NFOs dann gelesen werden. Alternativ: Jellyfin XML-Config auf Synology direkt lesen.
2. Falls WI-2 klappt → WI-1 (Enricher-Rewrite, Opus)
3. Plan in Issues #21/#22/#23 als Kommentare hinterlegt → GitHub als Referenz

## Reihenfolge Work Items
WI-2 → WI-1 (Opus) → WI-3 → WI-4 → WI-5
