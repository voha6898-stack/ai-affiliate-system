"""NordVPN affiliate uses TUNE/HasOffers platform — try correct API format."""
import urllib.request, urllib.error, json

API_KEY = "b17f388e71d20119bd3c18527d270a81e53a642da278174326a3cd25b7cdd139"

def try_req(label, url):
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read().decode()
            print(f"[{r.status}] {label}")
            try:
                data = json.loads(body)
                print(json.dumps(data, indent=2)[:600])
            except:
                print(body[:300])
            return body
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(f"[{e.code}] {label}: {body}")
    except Exception as e:
        print(f"[ERR] {label}: {e}")
    return None

print("=== TUNE/HasOffers API (NordVPN Affiliate) ===\n")

base = "https://affiliates.nordvpn.com"

# TUNE API endpoints
endpoints = [
    f"{base}/api.php?api_key={API_KEY}&Target=Publisher&Method=getPublishers",
    f"{base}/api.php?api_key={API_KEY}&Target=Affiliate&Method=findAll",
    f"{base}/api.php?api_key={API_KEY}&Target=AffiliateUser&Method=findAll",
    f"{base}/api/v1/publisher?api_key={API_KEY}",
    f"{base}/api/affiliate?api_key={API_KEY}",
]

for url in endpoints:
    label = url.split("Method=")[-1].split("&")[0] if "Method=" in url else url.split("/")[-1].split("?")[0]
    try_req(label, url)
    print()
