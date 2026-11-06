"""
Unit tests for PromptBuilder
"""
import pytest
from src.error_extractor import ErrorRegion
from src.prompt_builder import PromptBuilder


@pytest.fixture
def sample_region():
    return ErrorRegion(
        start_line=10,
        end_line=30,
        anchor_line=20,
        ecosystem="Python",
        error_type="KeyError",
        error_message="KeyError: 'stripe_charge_id'",
        culprit_file="src/payment_gateway.py",
        culprit_line=94,
        raw_snippet="src/payment_gateway.py:94: KeyError: 'stripe_charge_id'"
    )


def test_build_analysis_prompt(sample_region):
    builder = PromptBuilder()
    prompt = builder.build_analysis_prompt(sample_region, job_metadata={"runner": "ubuntu-latest", "job": "test"})
    assert "Detected Ecosystem: Python" in prompt
    assert "Candidate Offending File: src/payment_gateway.py" in prompt
    assert "Candidate Offending Line: 94" in prompt
    assert "ubuntu-latest" in prompt
    assert "=== EXTRACTED ERROR SNIPPET ===" in prompt


def test_truncate_oversized_snippet():
    builder = PromptBuilder()
    oversized = "\n".join([f"line_{i}: diagnostic log data message" for i in range(200)])
    truncated = builder.truncate_snippet(oversized, max_tokens=100)
    assert len(truncated.splitlines()) < 200
    assert "intermediate diagnostic lines omitted" in truncated


def test_full_request_payload(sample_region):
    builder = PromptBuilder()
    payload = builder.get_full_request_payload(sample_region)
    assert "system_prompt" in payload
    assert "user_prompt" in payload
    assert "JSON Schema:" in payload["system_prompt"]
    assert "Site Reliability Engineer" in payload["system_prompt"]
