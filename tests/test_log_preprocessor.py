"""
Unit tests for LogPreprocessor
"""
import pytest
from src.log_preprocessor import LogPreprocessor, PreprocessingMetrics


def test_strip_ansi_codes():
    raw = "\x1b[31;1mERROR:\x1b[0m Test \x1b[32mPASSED\x1b[0m \x1b[2K\x1b[1G"
    clean = LogPreprocessor.strip_ansi(raw)
    assert clean == "ERROR: Test PASSED "
    assert "\x1b" not in clean


def test_is_noisy_line():
    assert LogPreprocessor.is_noisy_line("  [=========================>            ] 48% eta 00:02") is True
    assert LogPreprocessor.is_noisy_line("Progress (12/45): 26.4%") is True
    assert LogPreprocessor.is_noisy_line("⠋ reify:@core/ui-kit-1: timing reifyNode") is True
    assert LogPreprocessor.is_noisy_line("npm http fetch GET 200 https://registry.npmjs.org/pkg 142ms") is True
    assert LogPreprocessor.is_noisy_line("Downloaded from central: https://repo.maven.apache.org/pkg.jar") is True
    assert LogPreprocessor.is_noisy_line("FAILED tests/test_payment.py::test_process_stripe_checkout") is False
    assert LogPreprocessor.is_noisy_line("KeyError: 'stripe_charge_id'") is False


def test_deduplicate_lines():
    lines = [
        "Normal line 1",
        "Repeated warning",
        "Repeated warning",
        "Repeated warning",
        "Repeated warning",
        "Repeated warning",
        "Normal line 2"
    ]
    deduped = LogPreprocessor.deduplicate_lines(lines, max_consecutive=2)
    assert len(deduped) < len(lines)
    assert "  [... repeated 3 times ...]" in deduped
    assert deduped[0] == "Normal line 1"
    assert deduped[-1] == "Normal line 2"


def test_clean_log():
    raw = """
\x1b[34m[INFO] Starting build...\x1b[0m
npm http fetch GET 200 https://registry.npmjs.org/pkg 100ms
  [=========================>            ] 50% eta 00:01
\x1b[31m[ERROR] Compilation failed at src/index.ts:12\x1b[0m
"""
    cleaned = LogPreprocessor.clean_log(raw, filter_noise=True)
    assert "\x1b" not in cleaned
    assert "npm http fetch" not in cleaned
    assert "[ERROR] Compilation failed at src/index.ts:12" in cleaned


def test_token_estimation_and_metrics():
    raw = "A " * 500  # 1000 chars, ~250 tokens
    clean = "A " * 50  # 100 chars, ~25 tokens
    metrics = LogPreprocessor.compute_metrics(raw, clean)
    assert metrics.raw_tokens > metrics.cleaned_tokens
    assert metrics.token_reduction_pct > 80.0
    assert metrics.byte_reduction_pct > 80.0
