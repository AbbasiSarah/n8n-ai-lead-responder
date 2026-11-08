"""Run with: python -m pytest"""
import json
import simulate as s


def test_offline_ai_sorts_enquiries():
    ai = json.loads(s.offline_ai("Ayesha", "Data Science", "fees kitni hai? I want to join next month"))
    assert ai["category"] == "Fees" and ai["priority"] == "high" and "Rs 25,000" in ai["reply"]
    ai = json.loads(s.offline_ai("Usman", "ML", "I am not happy, I want a refund"))
    assert ai["category"] == "Complaint" and ai["priority"] == "high"
    ai = json.loads(s.offline_ai("Omar", "-", "Do you offer Java courses?"))
    assert ai["category"] == "Other" and "personally" in ai["reply"]     # unknown -> human follow-up, no made-up answer


def test_read_ai_answer_handles_bad_output():
    good = s.read_ai_answer('Sure! {"category":"Fees","priority":"normal","reply":"Hi"}', "Ali")
    assert good["category"] == "Fees"
    bad = s.read_ai_answer("sorry, something went wrong", "Ali")
    assert bad["category"] == "Other" and "Ali" in bad["reply"]


def test_workflow_file_is_complete():
    wf = json.load(open("workflow.json"))
    names = {n["name"] for n in wf["nodes"]}
    assert {"Enquiry form", "Ask AI", "Read AI answer", "Save lead to Sheet", "Reply to customer", "Hot lead?", "Alert the owner"} <= names
    for src, out in wf["connections"].items():
        assert src in names
        assert all(c["node"] in names for branch in out["main"] for c in branch)


def test_python_uses_the_same_prompt_as_n8n():
    prompt = s.SYSTEM.split('system: "')[1].split('".replaceAll')[0].encode().decode("unicode_escape")
    assert prompt.startswith("You are the friendly enquiry assistant for {business}")
    assert "Never invent prices or dates." in prompt
