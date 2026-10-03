"""Try NordVPN affiliate API to get publisher info and affiliate links."""
import urllib.request, urllib.error, json, base64

API_KEY = "b17f388e71d20119bd3c18527d270a81e53a642da278174326a3cd25b7cdd139"

def try_req(label, url, headers):
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read().decode()
            print(f"[{r.status}] {label}")
            try:
                data = json.loads(body)
                print(json.dumps(data, indent=2)[:500])
            except:
                print(body[:300])
            return body
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(f"[{e.code}] {label}: {body}")
    except Exception as e:
        print(f"[ERR] {label}: {e}")
    return None

print("=== NordVPN Affiliate API ===\n")

# NordVPN affiliate direct API
for endpoint in [
    "https://affiliates.nordvpn.com/api/v1/publisher",
    "https://affiliates.nordvpn.com/api/publisher/links",
    "https://affiliates.nordvpn.com/api/v1/links",
    "https://affiliates.nordvpn.com/api/v1/me",
]:
    try_req(endpoint.split("/")[-1],
        endpoint,
        {"Authorization": f"Bearer {API_KEY}",
         "Accept": "application/json",
         "X-API-Key": API_KEY})
    print()
