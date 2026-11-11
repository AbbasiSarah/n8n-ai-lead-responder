"""Run the same lead-responder flow in Python, without n8n.

form enquiry -> AI writes a reply and sorts it -> save to leads.csv -> "send" the email -> alert the owner for hot leads

Two modes:
  * Real AI:  set AI_API_KEY and AI_MODEL and it calls the AI model, like the n8n workflow does.
  * Offline:  with no key, a simple keyword version stands in for the AI, so you can
              see the whole flow work for free. (It is clearly labelled as offline.)

Usage:
    python simulate.py                      # processes sample/enquiries.csv
"""
import csv
import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
BUSINESS = "Sunrise Tech Academy"
OWNER = "owner@example.com"
FACTS = {
    "fees": "Python for Beginners is Rs 15,000, Data Science and Web Development are Rs 25,000 each, and Machine Learning is Rs 35,000. You can pay in 2 instalments.",
    "timings": "Weekday classes run 6-8 pm Monday to Thursday, and weekend classes run 10 am-2 pm on Saturdays.",
    "admission": "New batches start on the 1st of every month. You can apply with the online form and pay the first instalment.",
    "online": "You can join online on Zoom or on campus in Islamabad. Every class is recorded.",
    "beginner": "No experience is needed for Python for Beginners or Web Development.",
}
SYSTEM = json.loads((HERE / "workflow.json").read_text())  # reuse the exact prompt from the n8n workflow
SYSTEM = [n for n in SYSTEM["nodes"] if n["name"] == "Ask AI"][0]["parameters"]["jsonBody"]


def ask_ai(name, course, message):
    """Same request the n8n 'Ask AI' node sends."""
    prompt = SYSTEM.split('system: "')[1].split('".replaceAll')[0].encode().decode("unicode_escape")
    prompt = prompt.replace("{business}", BUSINESS).replace("{facts}", " ".join(FACTS.values()))
    body = {"model": os.environ["AI_MODEL"], "max_tokens": 600, "system": prompt,
            "messages": [{"role": "user", "content": f"Name: {name}\nCourse: {course}\nMessage: {message}"}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": os.environ["AI_API_KEY"], "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["content"][0]["text"]


def offline_ai(name, course, message):
    """Stand-in for the AI when there's no API key: keyword rules + the same facts."""
    m = message.lower()
    topics = [k for k, words in {
        "fees": ["fee", "price", "cost", "kitni", "instal", "pay"], "timings": ["time", "timing", "weekend", "evening", "schedule"],
        "admission": ["join", "admission", "apply", "batch", "start", "enroll"], "online": ["online", "zoom", "campus", "home"],
        "beginner": ["beginner", "no experience", "new to", "never coded"]}.items() if any(w in m for w in words)]
    complaint = any(w in m for w in ["refund", "not happy", "disappointed", "complain", "bad experience"])
    hot = complaint or any(w in m for w in ["join", "ready", "next month", "this month", "asap", "today", "register"])
    category = "Complaint" if complaint else {"fees": "Fees", "timings": "Timings", "admission": "Admission", "online": "Course info",
                                              "beginner": "Course info"}.get(topics[0] if topics else "", "Other")
    lines = [FACTS[t] for t in topics] if topics and not complaint else []
    body = " ".join(lines) if lines else ("I'm sorry to hear that. Our team will call you personally today." if complaint
                                          else "Our team will reply to you personally within a day.")
    reply = f"Hi {name},\n\nThank you for contacting {BUSINESS}! {body}\n\nThe {BUSINESS} team"
    return json.dumps({"category": category, "priority": "high" if hot else "normal", "reply": reply})


def read_ai_answer(text, name):
    """Same as the n8n 'Read AI answer' node: parse JSON, or fall back to a safe reply."""
    try:
        return json.loads(text[text.index("{"): text.rindex("}") + 1])
    except ValueError:
        return {"category": "Other", "priority": "normal",
                "reply": f"Hi {name},\n\nThank you for contacting {BUSINESS}. Our team will reply to you personally within a day.\n\nThe {BUSINESS} team"}


def main():
    use_api = bool(os.environ.get("AI_API_KEY"))
    print(f"AI mode: {'AI API' if use_api else 'OFFLINE demo (no API key)'}\n")
    out, outbox = HERE / "sample" / "leads.csv", HERE / "sample" / "outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    with open(HERE / "sample" / "enquiries.csv", encoding="utf-8") as f:
        enquiries = list(csv.DictReader(f))
    rows = []
    for i, e in enumerate(enquiries, 1):
        text = ask_ai(e["Name"], e["Course"], e["Message"]) if use_api else offline_ai(e["Name"], e["Course"], e["Message"])
        ai = read_ai_answer(text, e["Name"])
        row = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "name": e["Name"], "email": e["Email"], "course": e["Course"],
               "message": e["Message"], "category": ai["category"], "priority": ai["priority"], "reply": ai["reply"]}
        rows.append(row)
        (outbox / f"{i:02d}_reply_to_{e['Name'].split()[0].lower()}.txt").write_text(
            f"To: {e['Email']}\nSubject: Thanks for contacting {BUSINESS}\n\n{ai['reply']}\n", encoding="utf-8")
        if ai["priority"] == "high":
            (outbox / f"{i:02d}_HOT_LEAD_alert.txt").write_text(
                f"To: {OWNER}\nSubject: Hot lead: {e['Name']} ({e['Course']})\n\n{e['Message']}\n", encoding="utf-8")
        print(f"{e['Name']:<15} {ai['category']:<12} {ai['priority']:<7} {'🔥 owner alerted' if ai['priority'] == 'high' else ''}")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\nSaved {len(rows)} leads to {out.relative_to(HERE)} and {len(list(outbox.glob('*.txt')))} emails to {outbox.relative_to(HERE)}/")


if __name__ == "__main__":
    main()
