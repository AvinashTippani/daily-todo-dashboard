"""Orchestrates the full daily pipeline: fetch → analyze → generate site."""
import json, os, sys
from datetime import datetime
from pathlib import Path

# Ensure scripts dir is on path when run from repo root
sys.path.insert(0, str(Path(__file__).parent))

from jira_fetcher      import fetch_jira
from confluence_fetcher import fetch_confluence
from teams_fetcher     import fetch_teams
from email_fetcher     import fetch_emails
from todo_generator    import generate_todos
from site_generator    import generate_site

def main():
    print("=" * 60)
    print(f"OD PM Daily To-Do Pipeline · {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")
    print("=" * 60)

    # ── 1. Fetch all sources ────────────────────────────────────────────────────
    raw_items = []

    print("\n[1/5] Fetching Jira…")
    try:
        jira = fetch_jira()
        print(f"  ✓ {len(jira)} Jira tickets")
        raw_items.extend(jira)
    except Exception as e:
        print(f"  ✗ Jira error: {e}")

    print("[2/5] Fetching Confluence…")
    try:
        conf = fetch_confluence()
        print(f"  ✓ {len(conf)} Confluence pages")
        raw_items.extend(conf)
    except Exception as e:
        print(f"  ✗ Confluence error: {e}")

    print("[3/5] Fetching Teams…")
    try:
        teams = fetch_teams()
        print(f"  ✓ {len(teams)} Teams messages")
        raw_items.extend(teams)
    except Exception as e:
        print(f"  ✗ Teams error: {e}")

    print("[4/5] Fetching Email…")
    try:
        emails = fetch_emails()
        print(f"  ✓ {len(emails)} emails")
        raw_items.extend(emails)
    except Exception as e:
        print(f"  ✗ Email error: {e}")

    print(f"\n  Total raw items: {len(raw_items)}")

    # ── 2. Analyze with Claude ──────────────────────────────────────────────────
    print("\n[5/5] Analyzing with Claude…")
    todos = generate_todos(raw_items)
    print(f"  ✓ {len(todos)} actionable to-dos")
    critical = sum(1 for t in todos if t["priority"] == "critical")
    high     = sum(1 for t in todos if t["priority"] == "high")
    print(f"  {critical} critical · {high} high · {len(todos)-critical-high} medium/low")

    # ── 3. Save data/todos.json ─────────────────────────────────────────────────
    Path("data").mkdir(exist_ok=True)
    payload = {
        "generated_at": datetime.now().isoformat(),
        "todos": todos,
    }
    with open("data/todos.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("\n  ✓ Saved data/todos.json")

    # ── 4. Generate index.html ──────────────────────────────────────────────────
    generate_site(todos, "index.html")
    print("  ✓ Saved index.html")

    print("\n✅ Pipeline complete!")

if __name__ == "__main__":
    main()
