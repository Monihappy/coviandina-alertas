import requests
import xml.etree.ElementTree as ET
import json
import os
import re
from datetime import datetime, timezone

RSS_SOURCES = [
    "https://xcancel.com/CoviandinaSAS/rss",
    "https://nitter.privacyredirect.com/CoviandinaSAS/rss",
    "https://nitter.poast.org/CoviandinaSAS/rss",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CoviandnaBot/1.0)"}

def detect_badge(text):
    t = text.lower()
    if any(w in t for w in ["cierre", "cerrad", "suspens", "bloqueo", "emergencia"]):
        return "danger"
    if any(w in t for w in ["restricc", "intervenc", "reduccion", "precaucion", "reducción", "precaución"]):
        return "warn"
    if any(w in t for w in ["habilitad", "reapert", "normaliz", "transit", "opera"]):
        return "ok"
    return "info"

def strip_html(html):
    clean = re.sub(r"<[^>]+>", " ", html)
    clean = (clean
             .replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
             .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
    return re.sub(r"\s{2,}", " ", clean).strip()

def fetch_from_source(url):
    r = requests.get(url, timeout=15, headers=HEADERS)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    items = root.findall(".//item")
    if not items:
        raise ValueError("Feed vacío")
    alerts = []
    for item in items[:6]:
        title       = item.findtext("title", "")
        description = item.findtext("description", "")
        link        = item.findtext("link", "https://x.com/CoviandinaSAS")
        pub_date    = item.findtext("pubDate", "")
        text        = strip_html(description or title)
        alerts.append({
            "text":    text,
            "link":    link.strip(),
            "pubDate": pub_date,
            "badge":   detect_badge(text)
        })
    return alerts

def main():
    result = None
    for src in RSS_SOURCES:
        try:
            alerts = fetch_from_source(src)
            result = {
                "status":    "ok",
                "source":    src,
                "updatedAt": datetime.now(timezone.utc).isoformat(),
                "alerts":    alerts
            }
            print(f"OK: {len(alerts)} alertas desde {src}")
            break
        except Exception as e:
            print(f"FALLO ({src}): {e}")

    if result:
        with open("alerts.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    else:
        # Mantener datos anteriores marcados como "stale" si existen
        if os.path.exists("alerts.json"):
            with open("alerts.json", "r", encoding="utf-8") as f:
                old = json.load(f)
            old["status"] = "stale"
            old["staleSince"] = datetime.now(timezone.utc).isoformat()
            with open("alerts.json", "w", encoding="utf-8") as f:
                json.dump(old, f, ensure_ascii=False, indent=2)
            print("Todas las fuentes fallaron. Conservando datos anteriores.")
        else:
            with open("alerts.json", "w", encoding="utf-8") as f:
                json.dump({"status": "error", "updatedAt": datetime.now(timezone.utc).isoformat(), "alerts": []}, f)
            print("Sin datos y sin respaldo. Archivo vacío generado.")

if __name__ == "__main__":
    main()
