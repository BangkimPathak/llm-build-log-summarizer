"""
Error Extractor Module
Performs semantic pattern recognition, multi-language stack trace detection,
error anchor identification, and contextual window slicing to isolate failure zones.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class ErrorRegion:
    start_line: int
    end_line: int
    anchor_line: int
    ecosystem: str
    error_type: str
    error_message: str
    culprit_file: Optional[str] = None
    culprit_line: Optional[int] = None
    raw_snippet: str = ""


# Multi-ecosystem signature regexes
ECOSYSTEM_SIGNATURES = {
    "Python": [
        (re.compile(r'Traceback \(most recent call last\):'), "Traceback"),
        (re.compile(r'E\s+([A-Za-z0-9_.]+(?:Error|Exception|Exit|Interrupt)): (.*)'), "PythonException"),
        (re.compile(r'FAILED (tests/[^\s:]+)::([^\s]+) - ([A-Za-z0-9_.]+(?:Error|Exception)?):? (.*)'), "PytestFailure"),
        (re.compile(r'===+ FAILURES ===+'), "PytestSection"),
    ],
    "Node.js": [
        (re.compile(r'ERROR in (\./[^\s:]+):(\d+):(\d+)'), "WebpackError"),
        (re.compile(r'(SyntaxError|TypeError|ReferenceError|RangeError): (.*)'), "JsException"),
        (re.compile(r'npm ERR! code (ELIFECYCLE|E404|ENOTFOUND)'), "NpmError"),
        (re.compile(r'TS\d{4,5}:\s*(.*)'), "TypeScriptError"),
    ],
    "Java": [
        (re.compile(r'\[ERROR\] (/[^\s:]+\.java):\[(\d+),(\d+)\] (.*)'), "JavaCompilerError"),
        (re.compile(r'(?:Caused by: )?([a-zA-Z0-9_.]+Exception): (.*)'), "JavaException"),
        (re.compile(r'\[INFO\] BUILD FAILURE'), "MavenBuildFailure"),
        (re.compile(r'\[ERROR\] COMPILATION ERROR'), "MavenCompilationError"),
    ],
    "Docker": [
        (re.compile(r'returned a non-zero code:\s*(137|1|2|127)'), "DockerNonZeroExit"),
        (re.compile(r'Out of memory: Killed process \d+ \(([^)]+)\)'), "OOMKilled"),
        (re.compile(r'cgroup OOM-killer \((.*)\)'), "CgroupOOM"),
    ],
    "General": [
        (re.compile(r'##\[error\](.*)'), "GitHubActionError"),
        (re.compile(r'Process completed with exit code (\d+)'), "ProcessExitCode"),
        (re.compile(r'fatal error:\s*(.*)'), "FatalError"),
        (re.compile(r'panic:\s*(.*)'), "GoPanic"),
    ]
}

# Regex to pinpoint culprit file and line
FILE_LINE_EXTRACTORS = [
    re.compile(r'([a-zA-Z0-9_\-./\\]+\.(?:py|tsx?|jsx?|java|rs|go|c|cpp)):(\d+)(?::(\d+))?'),
    re.compile(r'([a-zA-Z0-9_\-./\\]+\.java):\[(\d+),(\d+)\]'),
    re.compile(r'File "([^"]+)", line (\d+)'),
]


class ErrorExtractor:
    """Detects and slices contextual error regions from cleaned CI logs."""

    def __init__(self, pre_context_lines: int = 5, post_context_lines: int = 25):
        self.pre_context_lines = pre_context_lines
        self.post_context_lines = post_context_lines

    def detect_ecosystem(self, text: str) -> str:
        """Determines the primary ecosystem based on matching frequency."""
        counts = {eco: 0 for eco in ECOSYSTEM_SIGNATURES if eco != "General"}
        for eco, patterns in ECOSYSTEM_SIGNATURES.items():
            if eco == "General":
                continue
            for pattern, _ in patterns:
                matches = pattern.findall(text)
                counts[eco] += len(matches)

        best_eco = max(counts, key=counts.get)
        return best_eco if counts[best_eco] > 0 else "General"

    def find_anchors(self, lines: List[str]) -> List[Tuple[int, str, str, str]]:
        """
        Scans all lines for error anchors.
        Returns list of (line_idx, ecosystem, error_type, matched_message).
        """
        anchors = []
        for idx, line in enumerate(lines):
            for eco, patterns in ECOSYSTEM_SIGNATURES.items():
                for pattern, name in patterns:
                    m = pattern.search(line)
                    if m:
                        msg = line.strip()
                        anchors.append((idx, eco, name, msg))
                        break
        return anchors

    def merge_intervals(self, intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Merges overlapping line intervals to produce contiguous context slices."""
        if not intervals:
            return []
        sorted_intervals = sorted(intervals, key=lambda x: x[0])
        merged = [sorted_intervals[0]]
        for start, end in sorted_intervals[1:]:
            last_start, last_end = merged[-1]
            if start <= last_end + 3:  # bridge small gaps of 3 lines
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))
        return merged

    def extract_culprit(self, context_text: str) -> Tuple[Optional[str], Optional[int]]:
        """Extracts the most relevant culprit source file and line number from the context."""
        for pattern in FILE_LINE_EXTRACTORS:
            matches = list(pattern.finditer(context_text))
            if matches:
                # Prefer last mention (closest to bottom traceback in Python, or exact compiler error)
                match = matches[-1]
                filepath = match.group(1).replace('\\', '/')
                # Ignore virtualenv and node_modules internal paths if possible
                for m in reversed(matches):
                    fp = m.group(1).replace('\\', '/')
                    if "site-packages" not in fp and "node_modules" not in fp and ".venv" not in fp:
                        filepath = fp
                        match = m
                        break
                line_no = int(match.group(2))
                return filepath, line_no
        return None, None

    def extract_error_regions(self, text: str) -> List[ErrorRegion]:
        """
        Main extraction pipeline:
        Identifies anchors, expands context windows, merges overlapping ranges,
        and constructs structured ErrorRegion records.
        """
        lines = text.splitlines()
        total_lines = len(lines)
        if total_lines == 0:
            return []

        primary_eco = self.detect_ecosystem(text)
        anchors = self.find_anchors(lines)

        if not anchors:
            # Fallback: scan last 50 lines for any failure keywords
            for idx in range(max(0, total_lines - 50), total_lines):
                line_lower = lines[idx].lower()
                if any(k in line_lower for k in ["error", "failure", "failed", "exit code"]):
                    anchors.append((idx, primary_eco, "GeneralFailure", lines[idx]))
                    break

        if not anchors:
            return []

        # Create intervals around anchors
        intervals = []
        for idx, _, _, _ in anchors:
            start = max(0, idx - self.pre_context_lines)
            end = min(total_lines, idx + self.post_context_lines)
            intervals.append((start, end))

        merged_intervals = self.merge_intervals(intervals)
        regions: List[ErrorRegion] = []

        for start, end in merged_intervals:
            snippet_lines = lines[start:end]
            snippet = "\n".join(snippet_lines)

            # Determine best anchor in this slice
            slice_anchors = [a for a in anchors if start <= a[0] < end]
            primary_anchor = slice_anchors[0] if slice_anchors else (start, primary_eco, "Unknown", "")

            # Identify error type and message
            err_type = primary_anchor[2]
            err_msg = primary_anchor[3]
            # Try specific regex refinement
            for l in snippet_lines:
                for eco, patterns in ECOSYSTEM_SIGNATURES.items():
                    for pattern, name in patterns:
                        m = pattern.search(l)
                        if m:
                            if name == "PythonException":
                                err_type = m.group(1)
                                err_msg = l.strip()
                            elif name == "PytestFailure":
                                # group 3 or group 4 contains error class
                                err_type = m.group(3) if (m.lastindex and m.lastindex >= 3 and m.group(3)) else "PytestFailure"
                                err_msg = l.strip()
                            elif name in ["JsException", "JavaException"]:
                                err_type = m.group(1)
                                err_msg = l.strip()
                            elif name in ["OOMKilled", "DockerNonZeroExit"]:
                                err_type = "OOMKilled"
                                err_msg = l.strip()

            culprit_file, culprit_line = self.extract_culprit(snippet)

            regions.append(ErrorRegion(
                start_line=start + 1,
                end_line=end,
                anchor_line=primary_anchor[0] + 1,
                ecosystem=primary_eco,
                error_type=err_type,
                error_message=err_msg,
                culprit_file=culprit_file,
                culprit_line=culprit_line,
                raw_snippet=snippet
            ))

        return regions
