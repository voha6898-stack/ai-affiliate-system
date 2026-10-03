"""Deeper API key detection."""
import urllib.request, urllib.error, json, base64

API_KEY = "b17f388e71d20119bd3c18527d270a81e53a642da278174326a3cd25b7cdd139"

def try_req(label, url, headers={}, method="GET"):
    try:
        req = urllib.request.Request(url, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=8) as r:
            body = r.read().decode()
            print(f"[{r.status}] {label}")
            print(f"     {body[:300]}\n")
            return body
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        print(f"[{e.code}] {label}: {body}\n")
    except Exception as e:
        print(f"[ERR] {label}: {e}\n")
    return None

print("=== API Key Platform Detection ===\n")

# CJ Affiliate (Commission Junction)
try_req("CJ Affiliate",
    "https://commission-detail.api.cj.com/v3/commissions",
    {"Authorization": f"Bearer {API_KEY}"})

# Awin API
try_req("Awin",
    f"https://api.awin.com/accounts",
    {"Authorization": f"Bearer {API_KEY}"})

# Partnerize
try_req("Partnerize",
    "https://api.partnerize.com/v2/user/account",
    {"X-Api-Key": API_KEY})

# Impact - try with key as SID
b64 = base64.b64encode(f"{API_KEY}:{API_KEY}".encode()).decode()
try_req("Impact (key as SID)",
    f"https://api.impact.com/Mediapartners/{API_KEY}/Ads",
    {"Authorization": f"Basic {b64}"})

# ClickBank - key as dev key with test account
try_req("ClickBank (dev key header)",
    "https://api.clickbank.com/rest/1.3/products/list",
    {"Accept": "application/json",
     "DEV-KEY": API_KEY,
     "Authorization": API_KEY})
