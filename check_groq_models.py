"""Check available Groq models."""
import urllib.request, json, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("GROQ_API_KEY", "")
req = urllib.request.Request(
    "https://api.groq.com/openai/v1/models",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=10) as r:
    data = json.loads(r.read())

models = sorted([m["id"] for m in data["data"]])
print(f"Available Groq models ({len(models)}):")
for m in models:
    print(f"  {m}")
