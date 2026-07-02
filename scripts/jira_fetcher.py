"""Fetches Jira tickets assigned to or reported by the current user."""
import os
import requests

SITE     = os.environ["ATLASSIAN_SITE"]          # e.g. nice-ce-cxone-prod.atlassian.net
EMAIL    = os.environ["ATLASSIAN_EMAIL"]
TOKEN    = os.environ["ATLASSIAN_API_TOKEN"]
BASE_URL = f"https://{SITE}/rest/api/3"
AUTH     = (EMAIL, TOKEN)
HEADERS  = {"Accept": "application/json"}

FIELDS = "summary,description,status,priority,issuetype,updated,duedate,labels,components,comment,assignee"

def search(jql, max_results=30):
    resp = requests.get(
        f"{BASE_URL}/search",
        params={"jql": jql, "maxResults": max_results, "fields": FIELDS},
        auth=AUTH, headers=HEADERS, timeout=30
    )
    resp.raise_for_status()
    return resp.json().get("issues", [])

def fetch_jira():
    assigned = search(
        "assignee = currentUser() AND statusCategory != Done ORDER BY priority ASC, updated DESC",
        max_results=30
    )
    reported = search(
        "reporter = currentUser() AND statusCategory != Done AND updated >= -3d ORDER BY updated DESC",
        max_results=15
    )

    results = []
    seen = set()
    for issue in assigned + reported:
        key = issue["key"]
        if key in seen:
            continue
        seen.add(key)
        f = issue["fields"]
        latest_comment = ""
        comments = f.get("comment", {}).get("comments", [])
        if comments:
            latest_comment = comments[-1].get("body", "")
            if isinstance(latest_comment, dict):
                # Atlassian Document Format — extract plain text
                latest_comment = " ".join(
                    c.get("text", "") for block in latest_comment.get("content", [])
                    for c in block.get("content", []) if c.get("type") == "text"
                )
        results.append({
            "source": "jira",
            "key": key,
            "summary": f.get("summary", ""),
            "status": f.get("status", {}).get("name", ""),
            "priority": (f.get("priority") or {}).get("name", ""),
            "type": f.get("issuetype", {}).get("name", ""),
            "updated": f.get("updated", ""),
            "due": f.get("duedate", ""),
            "labels": f.get("labels", []),
            "components": [c["name"] for c in f.get("components", [])],
            "latest_comment": latest_comment[:500],
            "url": f"https://{SITE}/browse/{key}",
        })
    return results

if __name__ == "__main__":
    import json
    print(json.dumps(fetch_jira(), indent=2))
