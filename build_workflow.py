"""Writes workflow.json, the n8n workflow you import (n8n → Workflows → Import from file)."""
import json

SYSTEM = (
    "You are the friendly enquiry assistant for {business}. Read the customer's enquiry and reply ONLY with JSON: "
    '{"category": one of ["Fees", "Admission", "Course info", "Timings", "Complaint", "Other"], '
    '"priority": "high" if they want to join soon, are ready to pay, or are upset, otherwise "normal", '
    '"reply": a warm, short email reply (max 120 words) signed "The {business} team"}. '
    "Only use these facts: {facts}. If the answer isn't in the facts, say the team will reply personally within a day. Never invent prices or dates."
)

nodes = [
    {"id": "n1", "name": "Enquiry form", "type": "n8n-nodes-base.formTrigger", "typeVersion": 2.2, "position": [0, 300],
     "webhookId": "a3c1d8f2-5b7e-4c9a-9e21-lead-form0001",
     "parameters": {"formTitle": "Contact Sunrise Tech Academy", "formDescription": "Ask us anything. We reply within minutes.",
                    "formFields": {"values": [
                        {"fieldLabel": "Name", "requiredField": True},
                        {"fieldLabel": "Email", "fieldType": "email", "requiredField": True},
                        {"fieldLabel": "Course", "fieldType": "dropdown", "fieldOptions": {"values": [
                            {"option": "Python for Beginners"}, {"option": "Data Science"}, {"option": "Machine Learning"}, {"option": "Web Development"}, {"option": "Not sure yet"}]}},
                        {"fieldLabel": "Message", "fieldType": "textarea", "requiredField": True}]},
                    "options": {}}},
    {"id": "n2", "name": "Settings", "type": "n8n-nodes-base.set", "typeVersion": 3.4, "position": [220, 300],
     "parameters": {"assignments": {"assignments": [
         {"id": "s1", "name": "business", "value": "Sunrise Tech Academy", "type": "string"},
         {"id": "s2", "name": "owner_email", "value": "you@example.com", "type": "string"},
         {"id": "s3", "name": "model", "value": "claude-haiku-5-5", "type": "string"},
         {"id": "s4", "name": "facts", "type": "string", "value":
          "Courses: Python for Beginners (Rs 15,000, 6 weeks), Data Science (Rs 25,000, 10 weeks), Machine Learning (Rs 35,000, 12 weeks), "
          "Web Development (Rs 25,000, 10 weeks). Fees can be paid in 2 instalments. Weekday classes 6-8 pm Mon-Thu, weekend classes Sat 10 am-2 pm. "
          "Online (Zoom) or on campus in Islamabad. New batches start on the 1st of every month. No experience needed for Python or Web Development."}]},
         "includeOtherFields": True, "options": {}}},
    {"id": "n3", "name": "Ask AI", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": [440, 300],
     "parameters": {"method": "POST", "url": "https://api.anthropic.com/v1/messages",
                    "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
                    "sendHeaders": True, "headerParameters": {"parameters": [{"name": "anthropic-version", "value": "2023-06-01"}]},
                    "sendBody": True, "specifyBody": "json",
                    "jsonBody": "={{ JSON.stringify({ model: $json.model, max_tokens: 600, system: "
                                + json.dumps(SYSTEM) + ".replaceAll('{business}', $json.business).replace('{facts}', $json.facts), "
                                "messages: [{ role: 'user', content: 'Name: ' + $json.Name + '\\nCourse: ' + $json.Course + '\\nMessage: ' + $json.Message }] }) }}",
                    "options": {}}},
    {"id": "n4", "name": "Read AI answer", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [660, 300],
     "parameters": {"jsCode": """// Turn the AI's text into clean fields. If anything goes wrong, use a safe default reply.
const form = $('Settings').first().json;
const text = ($input.first().json.content || [{}])[0].text || '';
let ai;
try {
  ai = JSON.parse(text.slice(text.indexOf('{'), text.lastIndexOf('}') + 1));
} catch (e) {
  ai = { category: 'Other', priority: 'normal',
         reply: `Hi ${form.Name},\\n\\nThank you for contacting ${form.business}. Our team will reply to you personally within a day.\\n\\nThe ${form.business} team` };
}
return [{ json: {
  date: new Date().toISOString().slice(0, 16).replace('T', ' '),
  name: form.Name, email: form.Email, course: form.Course, message: form.Message,
  category: ai.category, priority: ai.priority, reply: ai.reply,
  owner_email: form.owner_email, business: form.business,
} }];"""}},
    {"id": "n5", "name": "Save lead to Sheet", "type": "n8n-nodes-base.googleSheets", "typeVersion": 4.6, "position": [880, 300],
     "parameters": {"operation": "append",
                    "documentId": {"__rl": True, "mode": "url", "value": "PASTE_YOUR_GOOGLE_SHEET_URL_HERE"},
                    "sheetName": {"__rl": True, "mode": "name", "value": "Leads"},
                    "columns": {"mappingMode": "defineBelow", "value": {
                        "date": "={{ $json.date }}", "name": "={{ $json.name }}", "email": "={{ $json.email }}", "course": "={{ $json.course }}",
                        "message": "={{ $json.message }}", "category": "={{ $json.category }}", "priority": "={{ $json.priority }}", "reply": "={{ $json.reply }}"},
                        "matchingColumns": [], "schema": [
                        {"id": c, "displayName": c, "required": False, "defaultMatch": False, "display": True, "type": "string", "canBeUsedToMatch": True}
                        for c in ["date", "name", "email", "course", "message", "category", "priority", "reply"]]},
                    "options": {}}},
    {"id": "n6", "name": "Reply to customer", "type": "n8n-nodes-base.gmail", "typeVersion": 2.1, "position": [1100, 300],
     "parameters": {"sendTo": "={{ $('Read AI answer').item.json.email }}",
                    "subject": "=Thanks for contacting {{ $('Read AI answer').item.json.business }}",
                    "emailType": "text", "message": "={{ $('Read AI answer').item.json.reply }}",
                    "options": {"appendAttribution": False}}},
    {"id": "n7", "name": "Hot lead?", "type": "n8n-nodes-base.if", "typeVersion": 2.2, "position": [1320, 300],
     "parameters": {"conditions": {"options": {"caseSensitive": False, "leftValue": "", "typeValidation": "loose", "version": 2},
                                   "conditions": [{"id": "c1", "leftValue": "={{ $('Read AI answer').item.json.priority }}", "rightValue": "high",
                                                   "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"},
                    "looseTypeValidation": True, "options": {}}},
    {"id": "n8", "name": "Alert the owner", "type": "n8n-nodes-base.gmail", "typeVersion": 2.1, "position": [1540, 200],
     "parameters": {"sendTo": "={{ $('Read AI answer').item.json.owner_email }}",
                    "subject": "=🔥 Hot lead: {{ $('Read AI answer').item.json.name }} ({{ $('Read AI answer').item.json.course }})",
                    "emailType": "text",
                    "message": "=New high-priority enquiry.\n\nName: {{ $('Read AI answer').item.json.name }}\nEmail: {{ $('Read AI answer').item.json.email }}\nCourse: {{ $('Read AI answer').item.json.course }}\nCategory: {{ $('Read AI answer').item.json.category }}\n\nMessage:\n{{ $('Read AI answer').item.json.message }}\n\nThe AI already replied to them. Follow up personally today!",
                    "options": {"appendAttribution": False}}},
    {"id": "n9", "name": "Read me first", "type": "n8n-nodes-base.stickyNote", "typeVersion": 1, "position": [-40, -40],
     "parameters": {"width": 620, "height": 260, "content":
        "## AI Lead Responder\nBuilt by Sara Abbasi · SheCodesAI\n\n1. **Settings**: change the business name, your email and the facts.\n"
        "2. **Ask AI**: add a *Header Auth* credential: name `x-api-key`, value = your Anthropic API key.\n"
        "3. **Save lead to Sheet**: connect Google, paste your Sheet URL. The sheet tab `Leads` needs the headers: date, name, email, course, message, category, priority, reply\n"
        "4. **Reply / Alert**: connect Gmail.\n5. Open the form URL from **Enquiry form** and test!"}},
]
conn = lambda a, b: {a: {"main": [[{"node": b, "type": "main", "index": 0}]]}}
connections = {}
for a, b in [("Enquiry form", "Settings"), ("Settings", "Ask AI"), ("Ask AI", "Read AI answer"), ("Read AI answer", "Save lead to Sheet"),
             ("Save lead to Sheet", "Reply to customer"), ("Reply to customer", "Hot lead?")]:
    connections.update(conn(a, b))
connections["Hot lead?"] = {"main": [[{"node": "Alert the owner", "type": "main", "index": 0}], []]}

wf = {"name": "AI Lead Responder (SheCodesAI)", "nodes": nodes, "connections": connections, "pinData": {},
      "settings": {"executionOrder": "v1"}, "active": False, "meta": {"templateCredsSetupCompleted": False}}
json.dump(wf, open("workflow.json", "w"), indent=2, ensure_ascii=False)
print("wrote workflow.json with", len(nodes), "nodes")
