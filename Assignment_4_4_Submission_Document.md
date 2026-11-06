# Document of Learnings: LLM-Based Build/Error-Log Summarization in CI/CD Pipelines

**Course:** Automation in Software Development (Semester V)  
**Institution:** Faculty of Engineering and Technology, Jain University  
**Student Name:** Bangkim Pathak  
**USN:** `24BTRAO006` (`24BTRO006`)  
**Course Instructor:** Munukuntla Shiva Prasad  
**Assignment Code:** 4.4 (`Assignment_4_4`)  
**Submission Date:** November 6, 2026  
**GitHub Repository Link:** [https://github.com/BangkimPathak/llm-build-log-summarizer](https://github.com/BangkimPathak/llm-build-log-summarizer)  
**Target CI Workflow:** [GitHub Actions CI Pipeline](https://github.com/BangkimPathak/llm-build-log-summarizer/actions)

---

## Table of Contents
1. [Executive Summary & Motivation](#1-executive-summary--motivation)
2. [Theoretical Foundations & Mathematical Formulation](#2-theoretical-foundations--mathematical-formulation)
3. [Step 1: Raw Log Ingestion & High-Speed Preprocessing](#3-step-1-raw-log-ingestion--high-speed-preprocessing)
4. [Step 2: Semantic Error Extraction & Context Window Slicing](#4-step-2-semantic-error-extraction--context-window-slicing)
5. [Step 3: Schema-Constrained Prompt Compilation & Token Budgeting](#5-step-3-schema-constrained-prompt-compilation--token-budgeting)
6. [Step 4: Resilient Diagnostic Engine (Gemini & Offline Heuristic Fallback)](#6-step-4-resilient-diagnostic-engine-gemini--offline-heuristic-fallback)
7. [Step 5: Automated CI Step Summary & PR Comment Generation](#7-step-5-automated-ci-step-summary--pr-comment-generation)
8. [Step 6: Empirical Benchmarking Across Multi-Language Failures](#8-step-6-empirical-benchmarking-across-multi-language-failures)
9. [Step 7: Automated Test Suite & Verification](#9-step-7-automated-test-suite--verification)
10. [Key Technical Learnings & DevOps Takeaways](#10-key-technical-learnings--devops-takeaways)
11. [Official Submission Verification & Links](#11-official-submission-verification--links)

---

## 1. Executive Summary & Motivation

Continuous Integration (CI) and Continuous Delivery (CD) systems like GitHub Actions, GitLab CI, and Jenkins are the backbone of modern automated software delivery. However, when automated builds or unit test jobs fail, developers encounter massive stdout/stderr log streams that frequently span **5,000 to over 50,000 lines**.

These raw logs are heavily contaminated with:
- **ANSI Terminal Escape Sequences:** Color formatting (`\x1b[31m`), cursor positioning (`\x1b[2K`), and screen clear markers.
- **Dynamic Download Artifacts:** Animated ASCII progress bars (`[====>  ] 45%`) and terminal spinner characters (`⠋`, `⠙`) produced by package managers (`pip`, `npm`, `maven`).
- **Repetitive Diagnostic Spam:** Repetitive dependency resolution traces, environment exports, and container image layer pull hashes.

### The Naive LLM Trap
While Large Language Models (LLMs) demonstrate extraordinary reasoning capabilities for software debugging, **forwarding raw 50,000-line logs directly to an LLM API introduces critical operational hazards:**
1. **Context Window Saturation:** Raw logs require 50,000 to 150,000 tokens per failed build, rapidly exceeding context limits or triggering heavy per-token API billing.
2. **"Needle-in-a-Haystack" Failure:** Excessive noise triggers attention degradation; the model often gets lost in benign warnings and fails to isolate the actual failure root cause.
3. **Severe Feedback Latency:** Processing 100k tokens over a remote API takes 20 to 60 seconds, unacceptable for rapid developer feedback loops.
4. **Third-Party API Outage Vulnerability:** Relying exclusively on an external LLM causes CI workflows to crash if the API key is missing, expired, or throttled.

### The Project Objective
This assignment designs, implements, and benchmarks a complete **LLM-Based Build/Error-Log Summarizer** that combines:
1. Deterministic high-speed log normalization (ANSI stripping, progress bar elimination, repetition deduplication).
2. Multi-language error signature extraction with context window slicing.
3. Token-budgeted JSON-schema prompt compilation.
4. Resilient multi-provider diagnosis featuring Google Gemini and a deterministic **Offline Heuristic Engine** fallback.
5. Automated generation of rich GitHub Actions Step Summaries (`$GITHUB_STEP_SUMMARY`) featuring actionable Git diff patches.

---

## 2. Theoretical Foundations & Mathematical Formulation

### 2.1 Context Distillation & Token Economics
Let $L_{\text{raw}}$ represent the raw log string of line count $N_{\text{raw}}$ and token volume $T_{\text{raw}}$. Let $L_{\text{dist}}$ denote the distilled error slice of line count $N_{\text{dist}}$ and token volume $T_{\text{dist}}$.

The **Token Bandwidth Reduction Ratio** ($\eta_T$) is defined as:
$$\eta_T = \left( 1 - \frac{T_{\text{dist}}}{T_{\text{raw}}} \right) \times 100\%$$

In production environments running $M = 10,000$ failed builds monthly, with LLM pricing $C_T$ per 1M input tokens, the monthly financial savings ($\Delta S_{\text{monthly}}$) is governed by:
$$\Delta S_{\text{monthly}} = M \cdot \frac{T_{\text{raw}} - T_{\text{dist}}}{10^6} \cdot C_T$$

At $C_T = \$2.50$, reducing raw token volume from 5,000 to 450 tokens per run yields a **91% reduction** in LLM operational costs while concurrently accelerating inference latency by an order of magnitude.

### 2.2 Interval Merging for Context Slicing
When multiple related error anchors are detected at line indices $a_1, a_2, \dots, a_k$, individual context windows are constructed:
$$I_j = \left[ \max(0, a_j - W_{\text{pre}}), \; \min(N, a_j + W_{\text{post}}) \right]$$
where $W_{\text{pre}} = 5$ and $W_{\text{post}} = 25$.

To prevent duplicate output chunks and preserve stack trace continuity, overlapping and adjacent intervals are merged:
$$I_a \cup I_b \quad \text{if} \quad \text{start}(I_b) \le \text{end}(I_a) + \delta$$
where $\delta = 3$ lines acts as an adjacency bridge for closely spaced stack frames.

---

## 3. Step 1: Raw Log Ingestion & High-Speed Preprocessing

The module [`src/log_preprocessor.py`](src/log_preprocessor.py) performs high-speed normalization without invoking expensive external libraries.

### Core Algorithmic Steps:
1. **ANSI Code Stripping:** Utilizes a compiled regular expression:
   ```python
   ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
   ```
   This strips all 8-bit and 24-bit ANSI color formatting, cursor movements, and line clearing codes.
2. **Dynamic Progress Bar Removal:** Identifies and filters transient download updates:
   - Python `pip` download status bars: `[=======>   ] 45%`
   - Maven download progress: `Progress (12/45): 26.4%`
   - Node `npm` and `yarn` timing logs: `⠋ reify:@core/ui-kit`
3. **Repetitive Line Deduplication:** Scans consecutive lines and collapses runaway retry loops or repeated warning logs into a clean indicator: `[... repeated N times: <line> ...]`.
4. **Token Estimation:** Calculates token density using a hybrid formula balancing byte count ($L / 4.0$) and word boundary density ($W \times 1.3$).

---

## 4. Step 2: Semantic Error Extraction & Context Window Slicing

The module [`src/error_extractor.py`](src/error_extractor.py) acts as a domain-aware semantic parser across diverse software engineering stacks.

### Multi-Ecosystem Signature Recognition:
- **Python / Pytest:** Detects `Traceback (most recent call last):`, `E   KeyError: '...'`, `FAILED tests/...`, and short test summaries.
- **Node.js / TypeScript / Webpack:** Detects `TS1005: ',' expected`, `ERROR in ./src/...:line:col`, and `SyntaxError`.
- **Docker / Containers:** Detects Linux kernel cgroup OOM termination: `Out of memory: Killed process`, and exit code `137`.
- **Java / Maven:** Detects `[ERROR] COMPILATION ERROR`, `cannot find symbol`, and `BUILD FAILURE`.

### Culprit Localization:
The extractor scans the matched error region with regex patterns:
```python
re.compile(r'([a-zA-Z0-9_\-./\\]+\.(?:py|tsx?|jsx?|java|rs|go)):(\d+)')
```
It intelligently ignores internal runtime paths (e.g. `node_modules`, `site-packages`, `.venv`) to pinpoint the exact user application source file and line responsible for the break.

---

## 5. Step 3: Schema-Constrained Prompt Compilation & Token Budgeting

The module [`src/prompt_builder.py`](src/prompt_builder.py) structures the extracted error snippet into a prompt designed for deterministic LLM parsing.

### Strict JSON Schema Constraint:
The system prompt instructs the LLM to assume the persona of a **Principal Site Reliability Engineer (SRE)** and enforces strict JSON output conforming to:
```json
{
  "status": "FAILURE",
  "ecosystem": "Python",
  "error_category": "KeyError",
  "culprit_file": "src/payment_gateway.py",
  "culprit_line": 94,
  "root_cause_explanation": "...",
  "remediation_steps": ["Step 1", "Step 2"],
  "suggested_diff_patch": "--- a/src/...\n+++ b/src/...",
  "confidence_score": 0.98
}
```

### Context Budgeting & Interior Truncation:
If a stack trace contains deep recursive calls exceeding the token budget ($T_{\text{max}} = 2500$), the builder preserves the top 12 lines (caller context) and bottom 20 lines (exact failure location and exception arguments), replacing intermediate frames with `[... N intermediate diagnostic lines omitted ...]`.

---

## 6. Step 4: Resilient Diagnostic Engine (Gemini & Offline Heuristic Fallback)

The module [`src/summarizer.py`](src/summarizer.py) provides a multi-tier provider architecture:

```
┌────────────────────────────────────────────────────────┐
│                   LogSummarizer                        │
└──────────────────────────┬─────────────────────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
  [Live Gemini Provider]      [Offline Heuristic Engine]
   (Requires API Key)          (Zero Network / Guaranteed)
             │                           ▲
             └──────(On Failure)─────────┘
```

1. **Google Gemini Provider (`gemini-1.5-flash`):** Uses Google's generative AI API with `temperature=0.1` and `responseMimeType="application/json"` for high-speed, reliable structured extraction.
2. **Offline Heuristic Provider:** An expert rule-based diagnostic engine. When run in air-gapped CI environments, student sandbox runners, or when API quotas are exceeded, this engine deterministically parses the extracted snippet and synthesizes accurate root causes and unified Git diff patches.
3. **Mock LLM Provider:** Enables instantaneous, deterministic unit testing and regression benchmarking.

---

## 7. Step 5: Automated CI Step Summary & PR Comment Generation

The module [`src/ci_formatter.py`](src/ci_formatter.py) transforms raw diagnostic objects into formatted developer deliverables:
- **`$GITHUB_STEP_SUMMARY` Integration:** Directly writes a Markdown diagnostic dashboard to the GitHub Actions job run summary.
- **Unified Diff Formatting:** Colorizes proposed code fixes in GitHub-flavored `diff` code blocks.
- **Actionable Remediation Checklist:** Outputs interactive markdown task checkboxes (`- [ ]`) enabling developers to verify remediation progress directly in pull request reviews.
- **JSON Serialization:** Emits machine-parseable JSON for integration with Slack webhooks, PagerDuty, or Datadog alerts.

---

## 8. Step 6: Empirical Benchmarking Across Multi-Language Failures

The script [`benchmark_summarizer.py`](benchmark_summarizer.py) systematically evaluated the summarization engine across 4 distinct CI build failures.

### Empirical Results Table

| Ecosystem & Failure Scenario | Raw Lines | Distilled Lines | Raw Tokens | Distilled Tokens | Token Savings (%) | Latency (ms) | Accuracy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Python (pytest KeyError)** | 224 | 117 | 2,556 | 585 | **77.11%** | 2.01 ms | **100%** |
| **Node.js (Webpack SyntaxError)** | 123 | 44 | 1,631 | 216 | **86.76%** | 1.11 ms | **100%** |
| **Docker (Exit 137 OOMKilled)** | 57 | 43 | 540 | 139 | **74.26%** | 0.49 ms | **100%** |
| **Java (Maven Missing Symbol)** | 110 | 66 | 1,618 | 301 | **81.40%** | 1.93 ms | **100%** |
| **AGGREGATE / AVERAGE** | **514** | **270** | **6,345** | **1,241** | **80.44%** | **1.38 ms** | **100%** |

### Benchmark Analysis:
1. **80.44% Token Reduction:** By removing ANSI formatting, download progress updates, and non-error lines, the engine eliminates over 80% of unnecessary LLM input tokens.
2. **Sub-2 Millisecond Processing:** The entire parsing, extraction, and heuristic synthesis pipeline executes in an average of **1.38 milliseconds**, adding practically zero overhead to the CI/CD pipeline.
3. **100% Diagnostic Accuracy:** In all 4 benchmark cases, the culprit file, line number, error classification, and root cause were identified with 100% precision.

---

## 9. Step 7: Automated Test Suite & Verification

The project includes an automated unit test suite executed via `pytest`:
- **`tests/test_log_preprocessor.py`:** Verifies ANSI stripping, noisy line detection, and repetition deduplication.
- **`tests/test_error_extractor.py`:** Tests language classification, interval merging, and culprit localization across Python, Node.js, Java, and Docker logs.
- **`tests/test_prompt_builder.py`:** Validates schema constraints, metadata injection, and interior middle-truncation.
- **`tests/test_summarizer.py`:** Verifies offline heuristic diagnoses, mock provider responses, and graceful Gemini fallback.
- **`tests/test_ci_formatter.py`:** Verifies markdown rendering, step summary writing, and JSON serialization.

### Pytest Execution Summary:
```text
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\documents\JAIN\SEM 5\Automation in  software devlopment\Exp\A_4_4
configfile: pytest.ini
testpaths: tests
collected 22 items

tests/test_ci_formatter.py::test_to_markdown PASSED                      [  4%]
tests/test_ci_formatter.py::test_write_step_summary PASSED               [  9%]
tests/test_ci_formatter.py::test_write_pr_comment PASSED                 [ 13%]
tests/test_ci_formatter.py::test_to_json PASSED                          [ 18%]
tests/test_error_extractor.py::test_detect_ecosystem PASSED              [ 22%]
tests/test_error_extractor.py::test_merge_intervals PASSED               [ 27%]
tests/test_error_extractor.py::test_extract_python_error_region PASSED   [ 31%]
tests/test_error_extractor.py::test_extract_node_syntax_error PASSED     [ 36%]
tests/test_error_extractor.py::test_extract_docker_oom PASSED            [ 40%]
tests/test_log_preprocessor.py::test_strip_ansi_codes PASSED             [ 45%]
tests/test_log_preprocessor.py::test_is_noisy_line PASSED                [ 50%]
tests/test_log_preprocessor.py::test_deduplicate_lines PASSED            [ 54%]
tests/test_log_preprocessor.py::test_clean_log PASSED                    [ 59%]
tests/test_log_preprocessor.py::test_token_estimation_and_metrics PASSED [ 63%]
tests/test_prompt_builder.py::test_build_analysis_prompt PASSED          [ 68%]
tests/test_prompt_builder.py::test_truncate_oversized_snippet PASSED     [ 72%]
tests/test_prompt_builder.py::test_full_request_payload PASSED           [ 77%]
tests/test_summarizer.py::test_offline_heuristic_python_keyerror PASSED  [ 81%]
tests/test_summarizer.py::test_offline_heuristic_docker_oom PASSED       [ 86%]
tests/test_summarizer.py::test_mock_llm_provider PASSED                  [ 90%]
tests/test_summarizer.py::test_gemini_provider_graceful_fallback_without_key PASSED [ 95%]
tests/test_summarizer.py::test_log_summarizer_end_to_end PASSED          [100%]

============================= 22 passed in 0.06s ==============================
```

---

## 10. Key Technical Learnings & DevOps Takeaways

1. **Pre-Filtering Is Non-Negotiable for Enterprise LLM Adoption:** Sending raw build logs to an LLM without pre-filtering wastes budget and reduces accuracy. Domain-specific regex filtering cuts token load by over 80% while sharpening model attention.
2. **Resilience Through Graceful Degradation:** A production CI/CD pipeline should never fail because an external AI API is down or throttled. Building a high-quality deterministic offline heuristic fallback ensures developers always receive actionable failure feedback.
3. **Actionable Fixes Over Verbose Explanations:** Developers do not want conversational paragraphs when a build fails; they want the offending file, line number, and a copy-pasteable Git diff or bash command to resolve it immediately.
4. **Platform Encoding Considerations:** CI environments run on varied operating systems (Ubuntu, Windows, macOS). Robust CLI tools must enforce UTF-8 streams (`sys.stdout.reconfigure(encoding='utf-8')`) to avoid console codec failures.

---

## 11. Official Submission Verification & Links

- **GitHub Repository URL:**  
  [https://github.com/BangkimPathak/llm-build-log-summarizer](https://github.com/BangkimPathak/llm-build-log-summarizer)
- **Target CI Workflow Actions:**  
  [https://github.com/BangkimPathak/llm-build-log-summarizer/actions](https://github.com/BangkimPathak/llm-build-log-summarizer/actions)
- **Student Metadata:**  
  - Name: **Bangkim Pathak**  
  - USN: **24BTRAO006** (`24BTRO006`)  
  - Branch: CSE / DevOps (Semester V)  
  - Institution: Faculty of Engineering and Technology, Jain University  
  - Course Instructor: **Munukuntla Shiva Prasad**
