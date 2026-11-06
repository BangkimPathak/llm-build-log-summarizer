"""
Log Preprocessor Module
Responsible for stripping ANSI terminal escape sequences, removing build spinners,
download progress bars, deduplicating repetitive diagnostic loops, and calculating
token metrics for LLM context optimization.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple


# Regex pattern to match ANSI escape codes (colors, cursor movements, screen clears)
ANSI_ESCAPE_PATTERN = re.compile(
    r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])'
)

# Regex pattern for interactive progress bars (e.g., [========>   ] 45%, eta 00:02)
PROGRESS_BAR_PATTERN = re.compile(
    r'(\[[=\->#\s]+\]\s*\d{1,3}%.*)|(Progress\s*\(\d+/\d+\):\s*\d+\.?\d*%)'
)

# Regex pattern for spinner and interactive terminal reset characters
SPINNER_PATTERN = re.compile(
    r'^[ \t]*[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏|/\\-]\s+.*'
)

# Common noisy CI build patterns that don't contribute to error diagnostics
NOISY_PATTERNS = [
    re.compile(r'^\s*npm http fetch (GET|POST|200|304)\s+'),
    re.compile(r'^\s*Downloaded from central:\s+https?://'),
    re.compile(r'^\s*\[pip\]\s+Downloading dependency\s+'),
    re.compile(r'^\s*---> Pulling layer\s+'),
    re.compile(r'^\s*Applying\s+[a-zA-Z0-9_.]+\.\.\.\s+OK'),
]


@dataclass
class PreprocessingMetrics:
    raw_lines: int
    cleaned_lines: int
    raw_bytes: int
    cleaned_bytes: int
    raw_tokens: int
    cleaned_tokens: int
    token_reduction_pct: float
    byte_reduction_pct: float


class LogPreprocessor:
    """Preprocesses raw CI/CD build logs to extract clean textual content."""

    @staticmethod
    def strip_ansi(text: str) -> str:
        """Removes all ANSI terminal color and control sequences."""
        return ANSI_ESCAPE_PATTERN.sub('', text)

    @classmethod
    def is_noisy_line(cls, line: str) -> bool:
        """Determines if a line is pure download progress or benign transient noise."""
        stripped = line.strip()
        if not stripped:
            return False

        if PROGRESS_BAR_PATTERN.search(stripped):
            return True
        if SPINNER_PATTERN.match(stripped):
            return True
        for pattern in NOISY_PATTERNS:
            if pattern.search(stripped):
                return True
        return False

    @classmethod
    def deduplicate_lines(cls, lines: List[str], max_consecutive: int = 2) -> List[str]:
        """
        Collapses repetitive duplicate log lines (e.g. loops or runaway retries)
        into a concise summary tag to prevent context explosion.
        """
        if not lines:
            return []

        deduped: List[str] = []
        repeat_count = 0
        last_line = None

        for line in lines:
            if line == last_line:
                repeat_count += 1
            else:
                if repeat_count > max_consecutive:
                    deduped.append(f"  [... repeated {repeat_count - max_consecutive} times ...]")
                repeat_count = 1
                last_line = line
                deduped.append(line)

        if repeat_count > max_consecutive:
            deduped.append(f"  [... repeated {repeat_count - max_consecutive} times ...]")

        return deduped

    @classmethod
    def clean_log(cls, raw_text: str, filter_noise: bool = True) -> str:
        """
        Full cleaning pipeline:
        1. Strip ANSI codes.
        2. Filter out download progress noise if filter_noise is True.
        3. Deduplicate repeating sequences.
        4. Normalize carriage returns and line breaks.
        """
        clean_text = cls.strip_ansi(raw_text)
        # Normalize Windows / Unix line breaks
        lines = [line.rstrip('\r') for line in clean_text.splitlines()]

        if filter_noise:
            filtered_lines = [line for line in lines if not cls.is_noisy_line(line)]
        else:
            filtered_lines = lines

        deduped_lines = cls.deduplicate_lines(filtered_lines)
        return "\n".join(deduped_lines)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Heuristic estimation of token count for LLM context budgeting.
        Rule of thumb: ~4 characters per token in standard English / source code.
        """
        if not text:
            return 0
        # Average between character-based estimation and word-based estimation
        char_tokens = len(text) / 4.0
        word_tokens = len(text.split()) * 1.3
        return max(1, int((char_tokens + word_tokens) / 2.0))

    @classmethod
    def compute_metrics(cls, raw_text: str, cleaned_text: str) -> PreprocessingMetrics:
        """Calculates comprehensive quantitative metrics before and after cleaning."""
        raw_lines = len(raw_text.splitlines())
        cleaned_lines = len(cleaned_text.splitlines())
        raw_bytes = len(raw_text.encode('utf-8'))
        cleaned_bytes = len(cleaned_text.encode('utf-8'))

        raw_tokens = cls.estimate_tokens(raw_text)
        cleaned_tokens = cls.estimate_tokens(cleaned_text)

        token_red = 0.0 if raw_tokens == 0 else max(0.0, ((raw_tokens - cleaned_tokens) / raw_tokens) * 100.0)
        byte_red = 0.0 if raw_bytes == 0 else max(0.0, ((raw_bytes - cleaned_bytes) / raw_bytes) * 100.0)

        return PreprocessingMetrics(
            raw_lines=raw_lines,
            cleaned_lines=cleaned_lines,
            raw_bytes=raw_bytes,
            cleaned_bytes=cleaned_bytes,
            raw_tokens=raw_tokens,
            cleaned_tokens=cleaned_tokens,
            token_reduction_pct=round(token_red, 2),
            byte_reduction_pct=round(byte_red, 2)
        )
