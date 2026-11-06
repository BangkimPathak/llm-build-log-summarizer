"""
Unit tests for CIFormatter
"""
import os
import json
import pytest
from src.summarizer import ErrorAnalysisResult
from src.ci_formatter import CIFormatter


@pytest.fixture
def sample_result():
    return ErrorAnalysisResult(
        status="FAILURE",
        ecosystem="Python",
        error_category="KeyError",
        culprit_file="src/payment_gateway.py",
        culprit_line=94,
        root_cause_explanation="Dictionary access response['stripe_charge_id'] failed because key is missing.",
        remediation_steps=[
            "Use response.get('stripe_charge_id')",
            "Implement fallback mock test payload"
        ],
        suggested_diff_patch="--- a/src/payment_gateway.py\n+++ b/src/payment_gateway.py\n@@ -94,1 +94,1 @@\n- err",
        confidence_score=0.98,
        provider_used="OfflineHeuristicProvider",
        analysis_latency_ms=12.4,
        raw_lines=500,
        cleaned_lines=45,
        raw_tokens=3200,
        distilled_tokens=280,
        token_savings_pct=91.25
    )


def test_to_markdown(sample_result):
    md = CIFormatter.to_markdown(sample_result)
    assert "## 🚨 Automated CI Build Failure Diagnostic Summary" in md
    assert "`src/payment_gateway.py:94`" in md
    assert "91.25% reduction" in md
    assert "```diff" in md
    assert "Bangkim Pathak" in md


def test_write_step_summary(sample_result, tmp_path):
    summary_file = tmp_path / "step_summary.md"
    written = CIFormatter.write_step_summary(sample_result, str(summary_file))
    assert written == str(summary_file)
    with open(summary_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Automated CI Build Failure Diagnostic Summary" in content


def test_write_pr_comment(sample_result, tmp_path):
    pr_comment_file = tmp_path / "pr_comment.md"
    CIFormatter.write_pr_comment(sample_result, str(pr_comment_file))
    with open(pr_comment_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Recommended Remediation Steps" in content


def test_to_json(sample_result):
    json_str = CIFormatter.to_json(sample_result)
    data = json.loads(json_str)
    assert data["status"] == "FAILURE"
    assert data["ecosystem"] == "Python"
    assert data["culprit_line"] == 94
    assert data["token_savings_pct"] == 91.25
