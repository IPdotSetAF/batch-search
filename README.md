# Batch Search

A zero-dependency Python CLI that searches a directory for a list of keywords and prints highlighted code blocks for every match — with filenames and line numbers.

---

## Features

- **Batch search** — provide any number of terms in a plain text file, one per line
- **Highlighted output** — matching text is visually highlighted in the terminal
- **Code block context** — shows surrounding lines so you always see the match in context
- **Smart block merging** — nearby matches in the same file are merged into one block instead of being shown separately
- **Recursive directory walk** — searches all files in subdirectories automatically
- **Binary file detection** — skips binary files automatically
- **Hidden file/directory skipping** — ignores anything starting with `.`
- **Extension filter** — optionally restrict the search to specific file types
- **Case-insensitive by default** — pass `--case-sensitive` to override
- **Pipe-friendly** — ANSI colours are automatically disabled when output is redirected

---

## Requirements

- Python 3.10+
- No third-party packages — uses only the standard library

---

## Usage

```
python batch-search.py <directory> <terms_file> [options]
```

### Positional arguments

| Argument | Description |
|---|---|
| `directory` | Root directory to search (searched recursively) |
| `terms_file` | Path to a text file containing search terms, one per line |

### Options

| Flag | Default | Description |
|---|---|---|
| `-c N`, `--context N` | `3` | Number of lines shown above and below each match |
| `--case-sensitive` | off | Match exact case instead of ignoring case |
| `--ext EXT [EXT ...]` | all files | Only search files with these extensions (e.g. `.py .js .ts`) |
| `--no-color` | off | Disable ANSI colour output |

---

## Examples

```bash
# Basic search
python batch-search.py ./src terms.txt

# Show 5 lines of context around each match
python batch-search.py ./src terms.txt -c 5

# Case-sensitive matching
python batch-search.py ./src terms.txt --case-sensitive

# Only search Python and JavaScript files
python batch-search.py ./src terms.txt --ext .py .js

# Save plain-text report to a file
python batch-search.py ./src terms.txt --no-color > report.txt
```

---

## Terms file format

Each line in the terms file is treated as a literal search term. Blank lines and lines starting with `#` are ignored.

```
# This is a comment and will be skipped

TODO
FIXME
deprecated
console.log
```

---

## Output format

```
Batch Search
Directory  : /path/to/src
Terms file : /path/to/terms.txt
Files      : 42
Terms      : 5
Context    : ±3 lines
Mode       : case-insensitive

══════════════════════════════════════════════════════════════════════════════════
  Search term : TODO
  3 match(es) across 2 file(s)
══════════════════════════════════════════════════════════════════════════════════

  utils/parser.py  lines 18–26  [match on line: 21]
──────────────────────────────────────────────────────────────────────────────────
      18 │ def parse_config(path):
      19 │     with open(path) as f:
      20 │         data = f.read()
  ►   21 │     # TODO: add validation here
      22 │     return data
      23 │
──────────────────────────────────────────────────────────────────────────────────
```

Each block shows:
- **Filename** (relative to the searched directory) and **line range**
- **Match line numbers** in brackets
- A `►` marker and yellow line number on every matching line
- The matched text highlighted in yellow on matching lines
- Dimmed context lines above and below

---

## Project structure

```
batch-search/
├── src/
│   └── batch-search.py        # Main script
├── batch-search.win.spec      # PyInstaller spec (Windows)
├── batch-search.linux.spec    # PyInstaller spec (Linux)
├── batch-search.macos.spec    # PyInstaller spec (macOS)
├── terms.txt                  # Example terms file
└── README.md
```
