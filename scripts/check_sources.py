#!/usr/bin/env python3
"""Täglicher Pilot-Check offizieller LU-Quellen ohne externe Python-Pakete.

- Lädt data/sources.json.
- Prüft offizielle HTML-Seiten und PDF-Dateien oder nur die Erreichbarkeit.
- Vergleicht stabilisierte Text-/PDF-Link-Hashes mit der letzten erfolgreichen Prüfung.
- Schreibt Änderungen in data/changes.json.
- Markiert HTTP-/Netzwerkfehler sichtbar, ohne den letzten guten Hash zu verlieren.

Ein geänderter Seiteninhalt ist KEIN Nachweis einer Rechtsänderung.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = ROOT / "data" / "sources.json"
CHANGES_PATH = ROOT / "data" / "changes.json"
TIMEOUT_SECONDS = 18
MAX_BYTES = 8 * 1024 * 1024
USER_AGENT = "SHB-Baugesetz-Monitor-Pilot/0.1 (einmal-taeglich; Kontakt ueber SHB Architekten)"


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


class ContentExtractor(HTMLParser):
    """Holt lesbaren Seitentext und PDF-Links ohne Script, Footer, Header etc."""

    SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside"}
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    NOISE = re.compile(r"cookie|breadcrumb|social|newsletter|tracking|navigation|toolbar", re.I)

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.skip_depth = 0
        self.tags: list[tuple[str, bool]] = []
        self.text: list[str] = []
        self.pdf_links: set[str] = set()

    def handle_starttag(self, tag, attrs):
        properties = dict(attrs)
        class_and_id = f"{properties.get('class', '')} {properties.get('id', '')}"
        skip = self.skip_depth > 0 or tag in self.SKIP_TAGS or bool(self.NOISE.search(class_and_id))
        if tag not in self.VOID_TAGS:
            self.tags.append((tag, skip))
            if skip:
                self.skip_depth += 1
        if not skip and tag == "a":
            href = properties.get("href", "")
            url = urljoin(self.base_url, href)
            if urlsplit(url).scheme in ("http", "https") and urlsplit(url).path.lower().endswith(".pdf"):
                self.pdf_links.add(urlsplit(url)._replace(fragment="").geturl())

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        # HTML ist häufig nicht sauber geschlossen. Nur passende Tags abbauen.
        for index in range(len(self.tags) - 1, -1, -1):
            if self.tags[index][0] == tag:
                discarded = self.tags[index:]
                self.tags = self.tags[:index]
                self.skip_depth -= sum(skipped for _, skipped in discarded)
                return

    def handle_data(self, data):
        if self.skip_depth == 0:
            piece = " ".join(html.unescape(data).split())
            if piece:
                self.text.append(piece)


def fetch(source: dict) -> tuple[int, bytes, str]:
    url = source["url"]
    if urlsplit(url).scheme not in ("http", "https"):
        raise ValueError("Nur offizielle HTTP(S)-Adressen erlaubt")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf,*/*;q=0.8"})
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        status = response.status
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Inhalt überschreitet 8 MB (Prüfung ausgesetzt)")
        charset = response.headers.get_content_charset() or "utf-8"
        return status, raw, charset


def analyse(source: dict, raw: bytes, charset: str) -> tuple[str, str, list[str]]:
    mode = source.get("check_mode", "html")
    if mode == "availability":
        return "", "", []
    if mode == "pdf":
        return sha256(raw), sha256(""), []
    if mode != "html":
        raise ValueError("Unbekannter check_mode: " + str(mode))
    page = raw.decode(charset, errors="replace")
    extractor = ContentExtractor(source["url"])
    extractor.feed(page)
    text = " ".join(extractor.text)
    text = re.sub(r"\s+", " ", text).strip()
    # Kein eigentlicher HTML-Inhalt (z.B. Javascript-Single-Page-App).
    if len(text) < 60:
        raise ValueError("Zu wenig auswertbarer HTML-Text; Seite benötigt Spezialprüfung")
    links = sorted(extractor.pdf_links)
    return sha256(text), sha256("\n".join(links)), links


def load_file(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} muss ein JSON-Objekt enthalten")
    return data


def save_file(path: Path, data: dict) -> None:
    target = path.with_suffix(".tmp")
    with target.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    target.replace(path)


def check(source: dict, history: list[dict]) -> None:
    now = timestamp()
    old_status = source.get("status", "ungeprüft")
    source["last_checked_at"] = now
    source["http_status"] = None

    try:
        status, raw, charset = fetch(source)
        source["http_status"] = status
        text_hash, pdf_hash, links = analyse(source, raw, charset)
        source.pop("error_message", None)
        old_hash = source.get("content_hash")
        old_links = source.get("pdf_links", [])
        mode = source.get("check_mode", "html")

        if mode == "availability":
            source["status"] = "erreichbar"
            source["last_change_summary"] = "Nur Erreichbarkeit geprüft; Inhalte nicht analysiert."
        elif not old_hash:
            source["content_hash"] = text_hash
            source["pdf_links_hash"] = pdf_hash
            source["pdf_links"] = links
            source["status"] = "erstprüfung"
            source["last_change_summary"] = "Erster Referenzstand gespeichert – noch kein Änderungsnachweis."
        else:
            changed = old_hash != text_hash or source.get("pdf_links_hash") != pdf_hash
            if changed:
                added = sorted(set(links) - set(old_links))
                removed = sorted(set(old_links) - set(links))
                if added:
                    summary = f"{len(added)} neuer PDF-Link(s) erkannt; Inhalte manuell prüfen."
                    kind = "pdf_added"
                elif removed:
                    summary = f"{len(removed)} PDF-Link(s) entfernt; Inhalte manuell prüfen."
                    kind = "pdf_removed"
                else:
                    summary = "Seiten- oder Dokumentinhalt verändert; fachlich prüfen."
                    kind = "content_changed"
                event = {
                    "source_id": source["id"], "municipality": source.get("municipality", ""),
                    "detected_at": now, "type": kind, "summary": summary,
                    "source_url": source["url"], "added_pdf_links": added,
                    "removed_pdf_links": removed, "requires_manual_review": True,
                }
                history.insert(0, event)
                source["last_change_detected_at"] = now
                source["last_change_summary"] = summary
                source["status"] = "geändert"
            else:
                source["status"] = "unverändert"
                if source.get("last_change_detected_at"):
                    # Zuletzt erkannte Änderung behalten, nicht mit 'keine Änderung' überschreiben.
                    source["last_change_summary"] = source.get("last_change_summary", "")
                else:
                    source["last_change_summary"] = "Seit der ersten Prüfung keine Änderung erkannt."
            source["content_hash"] = text_hash
            source["pdf_links_hash"] = pdf_hash
            source["pdf_links"] = links

    except HTTPError as error:
        source["http_status"] = error.code
        source["status"] = "fehler"
        source["error_message"] = f"HTTP {error.code}"
    except (URLError, TimeoutError, OSError, ValueError, UnicodeError) as error:
        source["status"] = "fehler"
        source["error_message"] = str(error)[:250]

    # Wiederkehrende Fehler nicht als wiederholte Rechts-/Seitenänderung speichern.
    if source["status"] == "fehler" and old_status != "fehler":
        history.insert(0, {
            "source_id": source["id"], "municipality": source.get("municipality", ""),
            "detected_at": now, "type": "check_failed",
            "summary": "Quelle nicht zuverlässig prüfbar: " + source.get("error_message", ""),
            "source_url": source["url"], "requires_manual_review": True,
        })


def main() -> int:
    data = load_file(SOURCES_PATH, {"meta": {}, "sources": []})
    if not isinstance(data.get("sources"), list):
        raise ValueError("sources.json muss eine Liste 'sources' enthalten")
    changes = load_file(CHANGES_PATH, {"changes": []})
    history = changes.get("changes", [])
    if not isinstance(history, list):
        history = []

    for i, source in enumerate(data["sources"], 1):
        print(f"[{i}/{len(data['sources'])}] {source.get('municipality', '')}: {source.get('title', '')}", flush=True)
        check(source, history)
        print(f"   -> {source['status']} (HTTP {source.get('http_status')})", flush=True)
        if i < len(data["sources"]):
            time.sleep(0.35)

    now = timestamp()
    data.setdefault("meta", {})["last_global_check"] = now
    data["meta"]["checker_version"] = "pilot-1.0"
    changes["changes"] = history[:300]
    changes["meta"] = {"last_updated_at": now}
    save_file(SOURCES_PATH, data)
    save_file(CHANGES_PATH, changes)
    print(f"Fertig: {len(data['sources'])} Quellen, Änderungen/Ereignisse: {len(history[:300])}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, json.JSONDecodeError, ValueError) as err:
        print(f"ABBRUCH: {err}", file=sys.stderr)
        sys.exit(1)
