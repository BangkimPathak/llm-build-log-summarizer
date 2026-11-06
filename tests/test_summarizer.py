"""
Unit tests for LogSummarizer and Diagnostic Providers
"""
import pytest
from src.summarizer import (
    LogSummarizer,
    OfflineHeuristicProvider,
    MockLLMProvider,
    GeminiProvider,
    ErrorAnalysisResult
)
from src.error_extractor import ErrorRegion


def test_offline_heuristic_python_keyerror():
    provider = OfflineHeuristicProvider()
    region = ErrorRegion(
        start_line=1, end_line=10, anchor_line=5,
        ecosystem="Python", error_type="KeyError",
        error_message="KeyError: 'stripe_charge_id'",
        culprit_file="src/payment_gateway.py",
        culprit_line=94,
        raw_snippet="src/payment_gateway.py:94: in charge\nKeyError: 'stripe_charge_id'"
    )
    res = provider.generate_analysis("system", "user", region)
    assert res["status"] == "FAILURE"
    assert res["ecosystem"] == "Python"
    assert res["error_category"] == "KeyError"
    assert res["culprit_file"] == "src/payment_gateway.py"
    assert res["culprit_line"] == 94
    assert "stripe_charge_id" in res["root_cause_explanation"]
    assert len(res["remediation_steps"]) >= 2
    assert "--- a/src/payment_gateway.py" in res["suggested_diff_patch"]


def test_offline_heuristic_docker_oom():
    provider = OfflineHeuristicProvider()
    region = ErrorRegion(
        start_line=1, end_line=10, anchor_line=5,
        ecosystem="Docker", error_type="OOMKilled",
        error_message="The command returned a non-zero code: 137",
        raw_snippet="Out of memory: Killed process 8421\nreturned a non-zero code: 137"
    )
    res = provider.generate_analysis("system", "user", region)
    assert res["status"] == "FAILURE"
    assert res["ecosystem"] == "Docker"
    assert "OOM" in res["error_category"]
    assert "CARGO_BUILD_JOBS" in res["remediation_steps"][0]


def test_mock_llm_provider():
    provider = MockLLMProvider()
    region = ErrorRegion(
        start_line=1, end_line=5, anchor_line=3,
        ecosystem="Node.js", error_type="SyntaxError",
        error_message="SyntaxError", culprit_file="app.js", culprit_line=12,
        raw_snippet="app.js:12 SyntaxError"
    )
    res = provider.generate_analysis("sys", "user", region)
    assert res["status"] == "FAILURE"
    assert res["culprit_file"] == "app.js"
    assert res["culprit_line"] == 12


def test_gemini_provider_graceful_fallback_without_key():
    provider = GeminiProvider(api_key=None)
    region = ErrorRegion(
        start_line=1, end_line=5, anchor_line=3,
        ecosystem="Python", error_type="KeyError",
        error_message="KeyError: 'tok'", culprit_file="auth.py", culprit_line=10,
        raw_snippet="KeyError: 'tok'"
    )
    res = provider.generate_analysis("sys", "user", region)
    assert res["status"] == "FAILURE"
    assert "offline_heuristic" in res["provider_fallback"]


def test_log_summarizer_end_to_end():
    summarizer = LogSummarizer(provider=OfflineHeuristicProvider())
    raw_log = """
\x1b[32m[INFO] Build starting...\x1b[0m
npm http fetch GET 200 https://registry.npmjs.org/pkg 142ms
  [=========================>            ] 48% eta 00:02
ERROR in ./src/components/CheckoutModal.tsx:42:15
TS1005: ',' expected.
> 42 |     dispatch({ type: 'CHECKOUT_SUCCESS' payload: token });
SyntaxError: Unexpected token, expected "," (42:40)
##[error]Process completed with exit code 2.
"""
    result: ErrorAnalysisResult = summarizer.summarize_log(raw_log)
    assert result.status == "FAILURE"
    assert result.ecosystem == "Node.js"
    assert result.error_category == "SyntaxError"
    assert "CheckoutModal.tsx" in result.culprit_file
    assert result.culprit_line == 42
    assert result.token_savings_pct > 0.0
    assert result.analysis_latency_ms > 0.0
