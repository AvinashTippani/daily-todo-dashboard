"""Fetches actionable emails from Outlook via Microsoft Graph."""
import os, re, requests
from datetime import datetime, timedelta, timezone

TENANT_ID     = os.environ["MS_TENANT_ID"]
CLIENT_ID     = os.environ["MS_CLIENT_ID"]
CLIENT_SECRET = os.environ["MS_CLIENT_SECRET"]
USER_ID       = os.environ["MS_USER_ID"]

GRAPH = "https://graph.microsoft.com/v1.0"

# Senders / subjects to skip (noise filters)
SKIP_SENDERS = ["jira@", "noreply@", "no-reply@", "notifications@", "linkedin", "donotreply"]
SKIP_SUBJECTS = ["linkedin", "newsletter", "booking confirmation", "all employees", "all-india"]

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

def strip_html(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()[:600]

def is_noise(email):
    sender = (email.get("from", {}).get("emailAddress", {}).get("address") or "").lower()
    subject = (email.get("subject") or "").lower()
    if any(s in sender for s in SKIP_SENDERS):
        return True
    if any(s in subject for s in SKIP_SUBJECTS):
        return True
    return False

def fetch_emails():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT00:00:00Z")

    results = []

    # Unread inbox emails
    try:
        resp = requests.get(
            f"{GRAPH}/users/{USER_ID}/mailFolders/Inbox/messages"
            f"?$filter=isRead eq false and receivedDateTime ge {cutoff}"
            f"&$top=25&$orderby=receivedDateTime desc"
            f"&$select=subject,from,receivedDateTime,bodyPreview,webLink,flag,importance",
            headers=headers, timeout=20
        )
        resp.raise_for_status()
        for email in resp.json().get("value", []):
            if is_noise(email):
                continue
            results.append({
                "source": "email",
                "subject": email.get("subject", ""),
                "from": (email.get("from", {}).get("emailAddress") or {}).get("name", ""),
                "from_email": (email.get("from", {}).get("emailAddress") or {}).get("address", ""),
                "body": email.get("bodyPreview", "")[:400],
                "updated": email.get("receivedDateTime", ""),
                "url": email.get("webLink", ""),
                "flagged": email.get("flag", {}).get("flagStatus") == "flagged",
                "importance": email.get("importance", "normal"),
            })
    except Exception as e:
        print(f"[email] inbox fetch error: {e}")

    # Flagged emails (older ones the user marked for follow-up)
    try:
        resp = requests.get(
            f"{GRAPH}/users/{USER_ID}/messages"
            f"?$filter=flag/flagStatus eq 'flagged'"
            f"&$top=10&$select=subject,from,receivedDateTime,bodyPreview,webLink",
            headers=headers, timeout=20
        )
        if resp.ok:
            for email in resp.json().get("value", []):
                if is_noise(email):
                    continue
                url = email.get("webLink", "")
                if any(r["url"] == url for r in results):
                    continue
                results.append({
                    "source": "email",
                    "subject": email.get("subject", ""),
                    "from": (email.get("from", {}).get("emailAddress") or {}).get("name", ""),
                    "from_email": (email.get("from", {}).get("emailAddress") or {}).get("address", ""),
                    "body": email.get("bodyPreview", "")[:400],
                    "updated": email.get("receivedDateTime", ""),
                    "url": url,
                    "flagged": True,
                    "importance": "high",
                })
    except Exception as e:
        print(f"[email] flagged fetch error: {e}")

    return results

if __name__ == "__main__":
    import json
    print(json.dumps(fetch_emails(), indent=2))
