#!/usr/bin/env python3
"""
Batch Search
------------
Search for terms (one per line in a terms file) across all files in a directory.
For each match, displays a highlighted code block with filename and line numbers.

Usage:
    python batch-search.py <directory> <terms_file> [options]
"""

import argparse
import os
import re
import sys

# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BG_YELLOW = "\033[43m"
    BG_RED = "\033[41m"
    BLACK = "\033[30m"

    @classmethod
    def disable(cls):
        """Strip all colour codes (plain-text mode)."""
        for attr in [a for a in vars(cls) if not a.startswith("_") and a != "disable"]:
            setattr(cls, attr, "")


def highlight(text: str, term: str, flags: int) -> str:
    """Wrap every occurrence of *term* in *text* with a visible highlight."""
    pattern = re.compile(re.escape(term), flags)

    def _replace(m):
        return f"{Colors.BG_YELLOW}{Colors.BLACK}{Colors.BOLD}{m.group()}{Colors.RESET}"

    return pattern.sub(_replace, text)


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------


def is_binary(path: str) -> bool:
    """Return True if the file looks like a binary (contains null bytes)."""
    try:
        with open(path, "rb") as fh:
            return b"\x00" in fh.read(8192)
    except OSError:
        return True


def iter_files(directory: str, extensions: list[str] | None) -> list[str]:
    """
    Walk *directory* recursively and return a sorted list of readable files.
    Hidden files/directories (starting with '.') are skipped.
    If *extensions* is given, only files whose suffix matches are included.
    """
    results = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in sorted(files):
            if name.startswith("."):
                continue
            if extensions and not any(name.endswith(e) for e in extensions):
                continue
            results.append(os.path.join(root, name))
    return results


def read_lines(path: str) -> list[str]:
    """Read all lines from *path*, returning [] on any error."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.readlines()
    except OSError:
        return []


# ---------------------------------------------------------------------------
# Core search logic
# ---------------------------------------------------------------------------


def find_blocks(lines: list[str], term: str, context: int, flags: int) -> list[dict]:
    """
    Return a list of *block* dicts, where each block is a contiguous region
    of lines that covers one or more matches, padded with *context* lines.

    Each block dict::
        {
            "start":   int,        # 0-based first line index (inclusive)
            "end":     int,        # 0-based last  line index (inclusive)
            "matches": list[int],  # 0-based indices of lines that matched
        }
    """
    pattern = re.compile(re.escape(term), flags)
    match_indices = [i for i, ln in enumerate(lines) if pattern.search(ln)]

    if not match_indices:
        return []

    blocks: list[dict] = []
    blk_start = max(0, match_indices[0] - context)
    blk_end = min(len(lines) - 1, match_indices[0] + context)
    blk_matches = [match_indices[0]]

    for idx in match_indices[1:]:
        new_start = max(0, idx - context)
        new_end = min(len(lines) - 1, idx + context)

        if new_start <= blk_end + 1:
            # Merge into the current block
            blk_end = new_end
            blk_matches.append(idx)
        else:
            blocks.append({"start": blk_start, "end": blk_end, "matches": blk_matches})
            blk_start = new_start
            blk_end = new_end
            blk_matches = [idx]

    blocks.append({"start": blk_start, "end": blk_end, "matches": blk_matches})
    return blocks


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

WIDTH = 82


def _rule(char: str = "─") -> str:
    return f"{Colors.DIM}{char * WIDTH}{Colors.RESET}"


def print_term_header(term: str, file_count: int, match_count: int) -> None:
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'═' * WIDTH}{Colors.RESET}")
    print(
        f"{Colors.BOLD}{Colors.CYAN}  Search term : {Colors.YELLOW}{term}{Colors.RESET}"
    )
    if match_count:
        print(
            f"{Colors.DIM}  {match_count} match(es) across "
            f"{file_count} file(s){Colors.RESET}"
        )
    else:
        print(f"{Colors.DIM}  No matches found{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'═' * WIDTH}{Colors.RESET}")


def print_block(
    block: dict,
    lines: list[str],
    term: str,
    rel_path: str,
    flags: int,
) -> None:
    match_set = set(block["matches"])
    start = block["start"]
    end = block["end"]
    match_lines = [i + 1 for i in block["matches"]]  # 1-based for display

    # File header
    line_range = f"{start + 1}" if start == end else f"{start + 1}–{end + 1}"
    print()
    print(
        f"  {Colors.BOLD}{Colors.GREEN}{rel_path}{Colors.RESET}  "
        f"{Colors.DIM}lines {line_range}{Colors.RESET}  "
        f"[{Colors.YELLOW}match on line"
        f"{'s' if len(match_lines) > 1 else ''}: "
        f"{', '.join(map(str, match_lines))}{Colors.RESET}]"
    )
    print(_rule())

    for offset, raw_line in enumerate(lines[start : end + 1]):
        abs_idx = start + offset
        line_num = abs_idx + 1  # 1-based
        text = raw_line.rstrip("\n")

        if abs_idx in match_set:
            gutter = f"{Colors.BOLD}{Colors.RED}►{Colors.RESET}"
            num_str = f"{Colors.BOLD}{Colors.YELLOW}{line_num:4d}{Colors.RESET}"
            body = highlight(text, term, flags)
        else:
            gutter = " "
            num_str = f"{Colors.DIM}{line_num:4d}{Colors.RESET}"
            body = f"{Colors.DIM}{text}{Colors.RESET}"

        print(f"  {gutter} {num_str} {Colors.DIM}│{Colors.RESET} {body}")

    print(_rule())


# ---------------------------------------------------------------------------
# Terms file
# ---------------------------------------------------------------------------


def load_terms(path: str) -> list[str]:
    """Read non-empty, non-comment lines from *path*."""
    try:
        with open(path, encoding="utf-8") as fh:
            return [
                ln.strip()
                for ln in fh
                if ln.strip() and not ln.lstrip().startswith("#")
            ]
    except OSError as exc:
        sys.exit(f"Error reading terms file: {exc}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    _name = os.path.basename(sys.argv[0])
    _cmd = f"python {_name}" if _name.endswith(".py") else _name

    parser = argparse.ArgumentParser(
        description=(
            "Search for terms across all files in a directory and display "
            "highlighted code blocks."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
examples:
  {_cmd} ./src terms.txt
  {_cmd} ./src terms.txt -c 5
  {_cmd} ./src terms.txt --case-sensitive
  {_cmd} ./src terms.txt --ext .py .js .ts
  {_cmd} ./src terms.txt --no-color > report.txt
        """,
    )
    parser.add_argument("directory", help="Directory to search in (recursive)")
    parser.add_argument("terms_file", help="Text file with one search term per line")
    parser.add_argument(
        "-c",
        "--context",
        type=int,
        default=3,
        metavar="N",
        help="Context lines shown above/below each match (default: 3)",
    )
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Use case-sensitive matching (default: case-insensitive)",
    )
    parser.add_argument(
        "--ext",
        nargs="+",
        metavar="EXT",
        help="Restrict search to files with these extensions, e.g. .py .js",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colour output (useful when redirecting to a file)",
    )

    args = parser.parse_args()

    # Disable colours when piping or explicitly requested
    if args.no_color or not sys.stdout.isatty():
        Colors.disable()

    # Validate paths
    if not os.path.isdir(args.directory):
        sys.exit(f"Error: '{args.directory}' is not a valid directory.")
    if not os.path.isfile(args.terms_file):
        sys.exit(f"Error: '{args.terms_file}' is not a valid file.")

    terms = load_terms(args.terms_file)
    if not terms:
        sys.exit("No search terms found in the terms file.")

    files = iter_files(args.directory, args.ext)
    if not files:
        sys.exit(f"No files found in '{args.directory}'.")

    re_flags = 0 if args.case_sensitive else re.IGNORECASE

    # ── Summary header ──────────────────────────────────────────────────────
    print(f"\n{Colors.BOLD}Batch Search{Colors.RESET}")
    print(f"{Colors.DIM}Directory  : {os.path.abspath(args.directory)}{Colors.RESET}")
    print(f"{Colors.DIM}Terms file : {os.path.abspath(args.terms_file)}{Colors.RESET}")
    print(f"{Colors.DIM}Files      : {len(files)}{Colors.RESET}")
    print(f"{Colors.DIM}Terms      : {len(terms)}{Colors.RESET}")
    print(f"{Colors.DIM}Context    : ±{args.context} lines{Colors.RESET}")
    print(
        f"{Colors.DIM}Mode       : "
        f"{'case-sensitive' if args.case_sensitive else 'case-insensitive'}"
        f"{Colors.RESET}"
    )

    grand_matches = 0

    # ── Per-term search ──────────────────────────────────────────────────────
    for term in terms:
        file_count = 0
        match_count = 0
        results: list[tuple[str, list[dict], list[str]]] = []

        for filepath in files:
            if is_binary(filepath):
                continue
            lines = read_lines(filepath)
            if not lines:
                continue
            blocks = find_blocks(lines, term, args.context, re_flags)
            if blocks:
                file_count += 1
                match_count += sum(len(b["matches"]) for b in blocks)
                results.append((filepath, blocks, lines))

        print_term_header(term, file_count, match_count)
        grand_matches += match_count

        for filepath, blocks, lines in results:
            rel = os.path.relpath(filepath, args.directory)
            for block in blocks:
                print_block(block, lines, term, rel, re_flags)

    # ── Grand total ──────────────────────────────────────────────────────────
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{'═' * WIDTH}{Colors.RESET}")
    print(
        f"{Colors.BOLD}  Grand total : "
        f"{Colors.YELLOW}{grand_matches} match(es){Colors.RESET}"
        f"{Colors.DIM} across {len(terms)} term(s) in {len(files)} file(s)"
        f"{Colors.RESET}"
    )
    print(f"{Colors.BOLD}{Colors.CYAN}{'═' * WIDTH}{Colors.RESET}\n")


if __name__ == "__main__":
    main()
