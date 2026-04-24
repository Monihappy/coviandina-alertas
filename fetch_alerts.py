import requests
import json
import os
import re
from datetime import datetime, timezone

# URL oculta de Twitter para leer tuits públicos (usada por sus widgets)
TWITTER_SYNDICATION_URL = "https://cdn.syndication.twimg.com/tweet-result?id=1" # Base URL
USER_SCREEN_NAME = "CoviandinaSAS"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def detect_badge(text):
    t = text.lower()
    if any(w in t for w in ["cierre", "cerrad", "suspens", "bloqueo", "emergencia"]):
        return "danger" # Rojo
    if any(w in t for w in ["restricc", "intervenc", "reduccion", "precaucion", "reducción", "precaución"]):
        return "warn"   # Amarillo
    if any(w in t for w in ["habilitad", "reapert", "normaliz", "transit", "opera"]):
        return "ok"     # Verde
    return "info"       # Azul

def fetch_latest_tweets():
    # Usamos el endpoint de syndication que no requiere API Keys
    url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{USER_SCREEN_NAME}"
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    
    # Extraer el JSON oculto en el HTML
    html_content = r.text
    json_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html_content)
    
    if not json_match:
        raise ValueError("No se pudo extraer el JSON de Twitter")
        
    data = json.loads(json_match.group(1))
    
    # Navegar por el JSON (Estructura de timeline)
    instructions = data['props']['pageProps']['timeline']['entries']
    
    alerts = []
    for entry in instructions[:6]: # Tomar los últimos 6
        try:
            if 'tweet' in entry['content']['tweet']:
                tweet_data = entry['content']['tweet']
                text = tweet_data['full_text']
                id_str = tweet_data['id_str']
                created_at = tweet_data['created_at']
                link = f"https://x.com/{USER_SCREEN_NAME}/status/{id_str}"
                
                alerts.append({
                    "text": text,
                    "link": link,
                    "pubDate": created_at,
                    "badge": detect_badge(text)
                })
        except KeyError:
            continue
            
    if not alerts:
        raise ValueError("Timeline vacío o estructura cambiada")
        
    return alerts

def main():
    try:
        print(f"Obteniendo tuits públicos de @{USER_SCREEN_NAME}...")
        alerts = fetch_latest_tweets()
        
        result = {
            "status": "ok",
            "source": "twitter_syndication",
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "alerts": alerts
        }
        
        with open("alerts.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        print(f"ÉXITO: Se guardaron {len(alerts)} alertas.")
        
    except Exception as e:
        print(f"FALLO: {e}")
        
        # Mantener datos anteriores si falla
        if os.path.exists("alerts.json"):
            with open("alerts.json", "r", encoding="utf-8") as f:
                old = json.load(f)
            old["status"] = "stale"
            old["staleSince"] = datetime.now(timezone.utc).isoformat()
            with open("alerts.json", "w", encoding="utf-8") as f:
                json.dump(old, f, ensure_ascii=False, indent=2)
            print("Conservando datos anteriores.")
        else:
            with open("alerts.json", "w", encoding="utf-8") as f:
                json.dump({"status": "error", "updatedAt": datetime.now(timezone.utc).isoformat(), "alerts": []}, f)

if __name__ == "__main__":
    main()
