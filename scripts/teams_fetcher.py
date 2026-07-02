"""Fetches recent Teams messages via Microsoft Graph API (client credentials)."""
import os, requests
from datetime import datetime, timedelta, timezone

TENANT_ID     = os.environ["MS_TENANT_ID"]
CLIENT_ID     = os.environ["MS_CLIENT_ID"]
CLIENT_SECRET = os.environ["MS_CLIENT_SECRET"]
USER_ID       = os.environ["MS_USER_ID"]   # Azure AD Object ID of Avinash
USER_EMAIL    = os.environ.get("ATLASSIAN_EMAIL", "")

GRAPH = "https://graph.microsoft.com/v1.0"

def get_token():
    resp = requests.post(
        f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def fetch_teams():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    results = []

    # ── 1:1 chats ──────────────────────────────────────────────────────────────
    try:
        chats_resp = requests.get(
            f"{GRAPH}/users/{USER_ID}/chats?$filter=chatType eq 'oneOnOne'&$top=20",
            headers=headers, timeout=20
        )
        chats_resp.raise_for_status()
        for chat in chats_resp.json().get("value", []):
            msgs_resp = requests.get(
                f"{GRAPH}/users/{USER_ID}/chats/{chat['id']}/messages"
                f"?$top=10&$filter=createdDateTime ge {cutoff}",
                headers=headers, timeout=20
            )
            if not msgs_resp.ok:
                continue
            for msg in msgs_resp.json().get("value", []):
                sender = (msg.get("from") or {}).get("user", {}).get("displayName", "")
                if sender == "Avinash Tippani":
                    continue  # skip own messages
                body = msg.get("body", {}).get("content", "")
                body = re.sub(r"<[^>]+>", " ", body).strip() if body else ""
                if len(body) < 5:
                    continue
                results.append({
                    "source": "teams",
                    "type": "chat",
                    "from": sender,
                    "body": body[:600],
                    "updated": msg.get("createdDateTime", ""),
                    "url": "",
                })
    except Exception as e:
        print(f"[teams] chat fetch error: {e}")

    # ── Channel @mentions ───────────────────────────────────────────────────────
    try:
        import re
        mentions_resp = requests.get(
            f"{GRAPH}/users/{USER_ID}/chats/getAllMessages"
            f"?$filter=createdDateTime ge {cutoff}&$top=20",
            headers=headers, timeout=20
        )
        if mentions_resp.ok:
            for msg in mentions_resp.json().get("value", []):
                mentions = [m for m in msg.get("mentions", [])
                            if (m.get("mentioned", {}).get("user") or {}).get("id") == USER_ID]
                if not mentions:
                    continue
                sender = (msg.get("from") or {}).get("user", {}).get("displayName", "")
                body = msg.get("body", {}).get("content", "")
                body = re.sub(r"<[^>]+>", " ", body).strip() if body else ""
                results.append({
                    "source": "teams",
                    "type": "mention",
                    "from": sender,
                    "body": body[:600],
                    "updated": msg.get("createdDateTime", ""),
                    "url": "",
                })
    except Exception as e:
        print(f"[teams] mention fetch error: {e}")

    return results

if __name__ == "__main__":
    import json, re
    print(json.dumps(fetch_teams(), indent=2))
