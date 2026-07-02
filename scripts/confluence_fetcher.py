"""Fetches recently-updated Confluence pages the user contributed to."""
import os, re, requests

SITE     = os.environ["ATLASSIAN_SITE"]
EMAIL    = os.environ["ATLASSIAN_EMAIL"]
TOKEN    = os.environ["ATLASSIAN_API_TOKEN"]
BASE_URL = f"https://{SITE}/wiki/rest/api"
AUTH     = (EMAIL, TOKEN)
HEADERS  = {"Accept": "application/json"}

def strip_html(html: str) -> str:
    """Very light HTML stripper for Confluence storage format."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()[:800]

def fetch_confluence():
    cql = (
        'contributor = currentUser() AND lastmodified >= now("-3d") '
        'AND type = page ORDER BY lastmodified DESC'
    )
    resp = requests.get(
        f"{BASE_URL}/content/search",
        params={"cql": cql, "limit": 15, "expand": "body.storage,space,version"},
        auth=AUTH, headers=HEADERS, timeout=30
    )
    resp.raise_for_status()
    pages = resp.json().get("results", [])

    results = []
    for page in pages:
        body_html = page.get("body", {}).get("storage", {}).get("value", "")
        results.append({
            "source": "confluence",
            "id": page["id"],
            "title": page["title"],
            "space": page.get("space", {}).get("name", ""),
            "updated": page.get("version", {}).get("when", ""),
            "url": f"https://{SITE}/wiki{page.get('_links', {}).get('webui', '')}",
            "summary": strip_html(body_html),
        })
    return results

if __name__ == "__main__":
    import json
    print(json.dumps(fetch_confluence(), indent=2))
