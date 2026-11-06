"""
CLI Entrypoint for LLM-Based Build/Error-Log Summarizer.
Usage:
    python -m src --log-file sample_logs/python_pytest_failure.log --step-summary
    python -m src --log-file build.log --output-summary summary.md --output-json summary.json
"""
import argparse
import sys

# Ensure UTF-8 output encoding across Windows PowerShell and CI environments
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from src.summarizer import LogSummarizer, OfflineHeuristicProvider, GeminiProvider, MockLLMProvider
from src.ci_formatter import CIFormatter


def main():
    parser = argparse.ArgumentParser(
        description="LLM-Based Build/Error-Log Summarizer for CI/CD Pipelines."
    )
    parser.add_argument(
        "--log-file", "-f",
        required=True,
        help="Path to the raw CI/CD build or test log file."
    )
    parser.add_argument(
        "--provider", "-p",
        choices=["heuristic", "gemini", "mock"],
        default="heuristic",
        help="Diagnostic engine provider (default: heuristic)."
    )
    parser.add_argument(
        "--output-summary", "-s",
        help="Optional path to write the formatted Markdown summary."
    )
    parser.add_argument(
        "--output-json", "-j",
        help="Optional path to write the raw JSON analysis result."
    )
    parser.add_argument(
        "--step-summary",
        action="store_true",
        help="Append summary directly to $GITHUB_STEP_SUMMARY."
    )

    args = parser.parse_args()

    # Select provider
    if args.provider == "gemini":
        provider = GeminiProvider()
    elif args.provider == "mock":
        provider = MockLLMProvider()
    else:
        provider = OfflineHeuristicProvider()

    summarizer = LogSummarizer(provider=provider)

    try:
        result = summarizer.summarize_file(args.log_file)
    except FileNotFoundError:
        print(f"Error: Log file not found at {args.log_file}", file=sys.stderr)
        sys.exit(1)

    # Output to stdout
    print(CIFormatter.to_markdown(result))

    # Optional file outputs
    if args.output_summary:
        with open(args.output_summary, "w", encoding="utf-8") as f:
            f.write(CIFormatter.to_markdown(result))
        print(f"\n[INFO] Wrote Markdown summary to: {args.output_summary}")

    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as f:
            f.write(CIFormatter.to_json(result))
        print(f"[INFO] Wrote JSON analysis to: {args.output_json}")

    if args.step_summary:
        written_path = CIFormatter.write_step_summary(result)
        if written_path:
            print(f"[INFO] Appended summary to $GITHUB_STEP_SUMMARY: {written_path}")


if __name__ == "__main__":
    main()
