import os, glob

files = glob.glob("docs/article/*/index.html")
if not files:
    print("No article files found")
    exit()

f = files[0]
with open(f, encoding="utf-8") as fh:
    html = fh.read()

print(f"Checking: {f}")
print(f"FAQPage schema:       {'YES' if 'FAQPage' in html else 'NO'}")
print(f"AggregateRating:      {'YES' if 'AggregateRating' in html else 'NO'}")
print(f"Review schema:        {'YES' if 'reviewRating' in html else 'NO'}")
print(f"Contextual links:     {html.count('font-weight:500')} found")
print(f"GA4 tag:              {'YES' if 'G-BRZJC88YQ1' in html else 'NO'}")
print(f"OneSignal:            {'YES' if 'onesignal' in html.lower() else 'NO (need ONESIGNAL_APP_ID)'}")
print(f"Internal rel links:   {html.count('/article/')} links")
