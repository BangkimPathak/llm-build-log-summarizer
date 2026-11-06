"""
Prompt Builder Module
Compiles few-shot, schema-constrained prompts for Large Language Models (LLMs)
to diagnose build failures, enforce JSON output schema, and manage context token budgets.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from src.error_extractor import ErrorRegion
from src.log_preprocessor import LogPreprocessor


SYSTEM_PROMPT = """You are a Principal Site Reliability Engineer (SRE) and Continuous Integration Architect.
Your task is to analyze the extracted CI/CD build error snippet, identify the single root cause,
and provide concrete, actionable remediation steps along with a unified Git diff code patch where applicable.

You MUST respond strictly with valid, well-formed JSON conforming to the following schema.
Do NOT enclose your response in Markdown code fences like ```json. Return ONLY raw JSON text.

JSON Schema:
{
  "status": "FAILURE",
  "ecosystem": "<Python | Node.js | Java | Docker | Rust | Go | CI/CD>",
  "error_category": "<Specific exception or failure category, e.g. KeyError, SyntaxError, OutOfMemory, MissingDependency>",
  "culprit_file": "<Relative path to the offending file or null if system/environment>",
  "culprit_line": <Line number as integer or null>,
  "root_cause_explanation": "<Concise 1-2 sentence explanation of why the build/test failed>",
  "remediation_steps": [
    "<Actionable step 1>",
    "<Actionable step 2>"
  ],
  "suggested_diff_patch": "<Unified git diff snippet showing proposed fix, or bash command if configuration>",
  "confidence_score": <Float between 0.0 and 1.0>
}
"""

FEW_SHOT_EXAMPLE = """
Example Input Error Snippet:
```
src/auth.py:45: in verify_token
    token = headers['Authorization'].split()[1]
KeyError: 'Authorization'
```

Example Output JSON:
{
  "status": "FAILURE",
  "ecosystem": "Python",
  "error_category": "KeyError",
  "culprit_file": "src/auth.py",
  "culprit_line": 45,
  "root_cause_explanation": "The request headers dictionary does not contain the 'Authorization' key, causing a KeyError when accessed directly.",
  "remediation_steps": [
    "Safely retrieve the Authorization header using headers.get('Authorization')",
    "Return a 401 Unauthorized response if the header is missing or malformed"
  ],
  "suggested_diff_patch": "--- a/src/auth.py\\n+++ b/src/auth.py\\n@@ -45,1 +45,3 @@\\n-    token = headers['Authorization'].split()[1]\\n+    auth_header = headers.get('Authorization')\\n+    if not auth_header:\\n+        return {'error': 'Missing Authorization header'}, 401\\n+    token = auth_header.split()[1]",
  "confidence_score": 0.98
}
"""


class PromptBuilder:
    """Builds token-budgeted, schema-constrained prompts for LLMs."""

    def __init__(self, max_prompt_tokens: int = 2500):
        self.max_prompt_tokens = max_prompt_tokens

    def truncate_snippet(self, snippet: str, max_tokens: int) -> str:
        """
        Truncates the middle of an oversized error snippet while keeping the
        initial caller context and final traceback/exception intact.
        """
        est_tokens = LogPreprocessor.estimate_tokens(snippet)
        if est_tokens <= max_tokens:
            return snippet

        lines = snippet.splitlines()
        if len(lines) <= 20:
            return snippet

        # Keep top 12 lines and bottom 20 lines
        head = lines[:12]
        tail = lines[-20:]
        omitted = len(lines) - 32
        return "\n".join(head + [f"\n[... {omitted} intermediate diagnostic lines omitted ...]\n"] + tail)

    def build_analysis_prompt(
        self,
        region: ErrorRegion,
        job_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Constructs the complete prompt payload for the LLM."""
        meta_str = ""
        if job_metadata:
            meta_str = f"CI Job Metadata:\n{json.dumps(job_metadata, indent=2)}\n\n"

        budget_for_snippet = max(500, self.max_prompt_tokens - 1000)
        bounded_snippet = self.truncate_snippet(region.raw_snippet, budget_for_snippet)

        user_content = f"""{meta_str}Detected Ecosystem: {region.ecosystem}
Candidate Offending File: {region.culprit_file or 'Unknown'}
Candidate Offending Line: {region.culprit_line or 'Unknown'}
Initial Classification: {region.error_type}

=== EXTRACTED ERROR SNIPPET ===
{bounded_snippet}
=== END ERROR SNIPPET ===

Analyze the error above and provide the root cause analysis in the required JSON schema.
"""
        return user_content.strip()

    def get_system_prompt(self) -> str:
        """Returns the system instruction prompt."""
        return SYSTEM_PROMPT.strip()

    def get_full_request_payload(
        self,
        region: ErrorRegion,
        job_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Returns paired system and user prompt dictionary."""
        return {
            "system_prompt": self.get_system_prompt(),
            "user_prompt": self.build_analysis_prompt(region, job_metadata)
        }
