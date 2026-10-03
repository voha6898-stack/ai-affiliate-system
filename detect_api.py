"""Auto-detect which affiliate platform this API key belongs to."""
import urllib.request, urllib.error, json, base64, sys

API_KEY = "b17f388e71d20119bd3c18527d270a81e53a642da278174326a3cd25b7cdd139"

def try_request(label, url, headers):
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as r:
            body = r.read().decode()
            print(f"[OK] {label}: {r.status}")
            print(f"     {body[:200]}")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:150]
        print(f"[{e.code}] {label}: {body}")
    except Exception as e:
        print(f"[ERR] {label}: {e}")
    return False

print("=== Detecting API key platform ===\n")

# 1. ClickBank API
try_request(
    "ClickBank",
    "https://api.clickbank.com/rest/1.3/accounts/",
    {"Accept": "application/json", "Authorization": API_KEY}
)

# 2. Impact (NordVPN platform) — needs SID, try with key as password
b64 = base64.b64encode(f":{API_KEY}".encode()).decode()
try_request(
    "Impact API",
    "https://api.impact.com/Mediapartners/",
    {"Authorization": f"Basic {b64}", "Accept": "application/json"}
)

# 3. ShareASale
try_request(
    "ShareASale",
    f"https://shareasale.com/x.cfm?action=getClickStats&apiKey={API_KEY}&affiliateId=&XMLFormat=1",
    {"Accept": "application/xml"}
)
