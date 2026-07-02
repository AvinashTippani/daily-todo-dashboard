"""Uses Claude to turn raw items into structured to-do entries."""
import json, os
import anthropic

MODEL = "claude-haiku-4-5-20251001"

SYSTEM = """You are a productivity assistant for Avinash Tippani, a Senior PM for Observability Dashboard (OD) at NICE.

Given a raw item from Jira, Confluence, Teams, or Outlook, output a JSON object (no markdown, no prose — only JSON).

Schema:
{
  "should_include": true/false,
  "title": "Short imperative action ≤60 chars, starts with a verb. Include ticket # if Jira.",
  "priority": "critical|high|medium|low",
  "source": "jira|teams|email|confluence",
  "category": "product|engineering|stakeholder|process|review",
  "estimated_effort": "5min|15min|30min|1h|2h+",
  "context": "2-3 sentences of background with ticket numbers and names.",
  "problem": "1-2 sentences on what specific gap needs addressing.",
  "solution": "1-2 sentences on recommended approach.",
  "action_plan": "1. Verb step\\n2. Verb step\\n3. Verb step\\n4. Verb step",
  "tags": ["tag1","tag2","tag3"],
  "source_url": "url or empty string"
}

Priority rules:
- critical: blocks a release today, on-call/XMatters duty, needs action within hours
- high: customer-reported P1/P2 bug, stakeholder waiting >4h, Ready-for-Dev ticket unassigned, launch readiness
- medium: important this sprint, requirements review, P3 bug, process/NPI actions
- low: FYI, resolved items needing a close-out note, informational updates

Skip (should_include=false): automated Jira notification emails, LinkedIn, all-company announcements, "ok"/"thanks" messages, emoji-only, already-resolved items with no action needed.

Avinash's key stakeholders: Ammon Lewis (PM), Tsahi (VP/Director), Matan Mizrahi (engineering), Avishay Robinov (engineering), Sherry Mashavi (engineering), Manthan Madannawar (engineering), Prakash Padadune (dependency owner).
Key projects: OD (Observability Dashboard), New Analytics, AI Agents Evaluations, Illumr, FedRAMP, CrossCX."""

def analyze_item(raw_item: dict) -> dict | None:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = f"Analyze this raw item and return only a JSON object:\n\n{json.dumps(raw_item, indent=2)}"
    msg = client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        result = json.loads(text)
        if result.get("should_include"):
            return result
    except json.JSONDecodeError:
        pass
    return None

def generate_todos(raw_items: list[dict]) -> list[dict]:
    todos = []
    for i, item in enumerate(raw_items):
        print(f"  Analyzing item {i+1}/{len(raw_items)}: {item.get('summary') or item.get('subject') or item.get('body','')[:50]}")
        result = analyze_item(item)
        if result:
            result["updated"] = item.get("updated", "")
            result["source_url"] = result.get("source_url") or item.get("url", "")
            todos.append(result)

    # Sort: critical → high → medium → low
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    todos.sort(key=lambda t: order.get(t.get("priority", "low"), 3))

    # Add sequential IDs
    for i, t in enumerate(todos):
        t["id"] = i + 1

    return todos
