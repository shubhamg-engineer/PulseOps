import pytest
import yaml
from pathlib import Path
from src.agent import process_agent_query, draft_work_order
from src.config import BASE_DIR

def load_test_questions():
    yaml_path = BASE_DIR / "tests" / "agent_questions.yaml"
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["questions"]

@pytest.mark.parametrize("q", load_test_questions())
def test_agent_qa_suite(q):
    res = process_agent_query(q["question"])
    
    # Verify expected status
    assert res["status"] == q["expected_status"], f"Question {q['id']} expected {q['expected_status']} got {res['status']}"
    
    # Verify expected contents in answer text
    answer_text = res["answer"]
    for expected_str in q["expected_contains"]:
        assert expected_str.lower() in answer_text.lower(), f"Question {q['id']} answer missing '{expected_str}'. Answer: {answer_text}"

def test_draft_work_order():
    draft = draft_work_order("AST_101", "Bearing wear")
    assert "error" not in draft
    assert draft["asset_id"] == "AST_101"
    assert "Bearing" in draft["required_part"]
    assert draft["requires_human_approval"] is True
    assert draft["estimated_cost_avoided_inr"] > 0
