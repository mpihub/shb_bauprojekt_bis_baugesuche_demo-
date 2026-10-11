# SHB Baugesetz-Updates Luzern – technischer Pilot

Dieses Paket erweitert die bisherige HTML-Demo um eine echte technische tägliche Quellenprüfung.

**Wichtig:** Das Fachnachschlagewerk (IVHB, hindernisfreies Bauen, datierte News) im HTML bleibt **redaktioneller Demo-Inhalt**. Der Bereich **«Tägliche Quellenprüfung»** lädt die echte JSON-Ausgabe des Prüfscripts. Das System beurteilt **keine Rechtsgültigkeit, Fristen oder Inkrafttretensdaten**.

## So wird der Pilot online eingerichtet (ohne Programmiererfahrung)

1. Ein kostenloses [GitHub-Konto](https://github.com/signup) erstellen.
2. [GitHub Desktop](https://desktop.github.com/) auf Windows oder macOS installieren.
3. Dieses ZIP **vollständig entpacken**. In GitHub Desktop `File → Add local repository…` auswählen und diesen Ordner wählen. Wenn GitHub Desktop anbietet, hier ein Repository anzulegen, bestätigen.
4. In GitHub Desktop die Dateien **committen** und danach `Publish repository` wählen. Für die kostenlose öffentliche GitHub-Pages-Testseite das Repository **Public** veröffentlichen. **Keine internen SHB-Daten oder personenbezogene Projektunterlagen hochladen.**
5. Im Browser das GitHub-Repository öffnen → `Settings → Pages`. Unter **Build and deployment** die Quelle **GitHub Actions** auswählen.
6. Den Reiter `Actions` öffnen → Workflow **SHB Baugesetz Pilot – Quellenprüfung und Veröffentlichung** → `Run workflow` → Start bestätigen.
7. Nach erfolgreichem Durchlauf unter `Settings → Pages` den Link `Visit site` öffnen. Die Webseite zeigt dann im Abschnitt **Tägliche Quellenprüfung** den tatsächlichen Prüflauf und die Ergebnisse.
8. Morgen oder übermorgen erneut prüfen, ob bei `Actions` ein neuer Lauf ausgeführt wurde. Die tägliche Prüfung ist für **05:17 UTC** geplant (07:17 Sommerzeit / 06:17 Winterzeit in Luzern), kann durch GitHub verzögert werden.

**Wichtig zu GitHub Pages:** Bei GitHub Free ist eine frei zugängliche Pages-Testwebsite der einfachste Weg. Für eine **nur intern sichtbare** Website bitte vor der Veröffentlichung geschütztes Hosting bzw. Unternehmenszugangssteuerung vorsehen. Ein privates GitHub-Repository bedeutet nicht automatisch eine privat zugängliche Pages-Website.

## Dateien

- `index.html`: bisherige Offline-Demo mit zusätzlichem Echtprüfungs-Abschnitt.
- `data/sources.json`: 20 erfasste **offizielle** Einstiegsquellen, Prüfstatus und Hashes.
- `data/changes.json`: Ereignisprotokoll (erst ab tatsächlich erkannten Änderungen).
- `scripts/check_sources.py`: Prüfmotor, benötigt nur Python 3.12 (Standardbibliothek).
- `.github/workflows/daily.yml`: läuft automatisch, speichert JSON und veröffentlicht Pages **im selben Workflow**.
- `requirements.txt`: leer; keine externen Python-Abhängigkeiten.

## Lokal prüfen

Python 3.12 installieren. Im entpackten Projektordner Terminal öffnen:

```bash
python scripts/check_sources.py
```

Das erste Ergebnis ist **«Erstprüfung»**. Bei erneutem Ausführen wird mit den gespeicherten Hashes verglichen.

Lokalen Webserver starten:

```bash
python -m http.server 8000
```

Dann im Browser `http://localhost:8000` öffnen. Direktes Öffnen via `file://` zeigt zwar die statische Demo, verhindert aber im Browser häufig den Zugriff auf `data/sources.json`.

## Was «Änderung erkannt» bedeutet

Das Script vergleicht sichtbaren HTML-Text und neu/entfernt verlinkte PDFs. Bei einem direkt überprüften PDF kann auch dessen Inhalt gehasht werden. Die Wirkung der Änderung auf Bau- oder Planungsrecht wird **nicht** automatisch beurteilt. Kartenanwendungen und Login-Seiten sind in der ersten Version teilweise nur auf **Erreichbarkeit** geprüft.

**Folgende Angaben sind auseinanderzuhalten:**
- `last_checked_at`: technischer Abrufzeitpunkt.
- `last_change_detected_at`: Zeitpunkt einer erkannten **technischen** Änderung.
- amtliches Publikationsdatum/Inkrafttreten: muss aus Originalquelle und Fachprüfung stammen.

## Typische Fehler

- **Actions rot:** Lauf anklicken, den fehlgeschlagenen Schritt und die Logausgabe öffnen. Bei `403` zum Git-Push Repository-Einstellungen für `Workflow permissions` prüfen.
- **Erste Prüfung meldet nichts:** korrekt; es gibt noch keinen Vergleichsstand.
- **Prüffehler bei einzelnen Webseiten:** häufig Bot-Schutz, dynamische Inhalte, Timeout oder geänderte URL. Diese Quellen brauchen später einen eigenen Prüftyp.
- **Keine neuen Daten online:** `Actions` prüfen (beide Jobs grün?) und `Settings → Pages` auf `GitHub Actions` einstellen. Auf der veröffentlichten Seite neu laden.
- **ÖREB/GIS zeigen nur erreichbar:** Kartendaten werden damit noch nicht inhaltlich verglichen.

## Grenzen der Pilotversion

- 20 Quellen, nicht alle Gemeinden und nicht alle PDFs.
- Keine rechtliche Auslegung und kein Nachweis von Rechtskraft oder Vollständigkeit.
- Kein Benutzerlogin und keine automatische Mailbenachrichtigung.
- Gemeindespezifische IVHB-Übergänge in der bestehenden Demo sind noch nicht täglich aktualisiert.
- Viele Änderungen am Navigations-/Portal-Text können Fehlalarme ergeben. Solche Quellen nach dem Pilot gezielt normalisieren.

## Nächste Entscheidung nach 2–4 Wochen

Welche Quellen liefern brauchbare Änderungen? Welche sind fehleranfällig? Welche weiteren Gemeinden und Gesuchsformulare braucht SHB? Dann erst ausbauen und einen fachlichen Freigabeprozess definieren.
