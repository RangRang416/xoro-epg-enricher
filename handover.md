# Handover — xoro-epg-enricher (2026-07-20)

Repo synchron (origin/main). `.gitignore` um Session-Export-Pattern ergänzt (commit `e390371`).

**#22/#35 diagnostiziert, NICHT geschlossen (Rubens Freigabe steht aus):**
- #22: Android-TV-App-Absturz, nicht unser Server. Root Cause: fehlende Null-Prüfung in `FullDetailsFragment.java:246`. Upstream-Report: jellyfin/jellyfin-androidtv#5700. Resume-Speicherung funktioniert korrekt (MinResumePct 5% erklärt die "leere Weiterschauen"-Beobachtung).
- #35: Mount reconnected automatisch alle 5 Min sobald PC online — kein Fix nötig, bewusst akzeptierte Grenze (kein WOL-Trigger bei NAS-Boot, Ruben-Entscheid).

Offen, unverändert seit 01.07. (nicht bearbeitet): zweiter Serien-Scan auf `buffalo-archiv/Filme II/Serien`-Rest, #32 Metadaten-Lücke.

Nebenbefund: claude-system#82 (MEMORY.md-Wachstum treibt Session-Start-Token hoch, 40k→60k) erstellt.
