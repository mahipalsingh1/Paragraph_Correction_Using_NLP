# utils/lexicon_loader.py
import csv
from pathlib import Path
from typing import Dict, List, Tuple

# --------------------
# Core helpers
# --------------------

def _clean_cell(s: str) -> str:
    """Trim, normalize inner spaces, and strip surrounding quotes."""
    if not isinstance(s, str):
        return ""
    s = s.strip().strip('"').strip("'")
    # Normalize multi-spaces inside names like "Jammu  and   Kashmir"
    s = " ".join(s.split())
    return s

def _read_rows(path: Path) -> List[List[str]]:
    """Read CSV into list of string lists, ignoring empty cells, BOMs, and comment lines."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig") as f:
        rdr = csv.reader(f)
        rows = []
        for row in rdr:
            if not row:
                continue
            # Skip comment lines that start with '#'
            first_nonempty = next((c for c in row if _clean_cell(c)), "")
            if first_nonempty.startswith("#"):
                continue
            cells = [_clean_cell(c) for c in row if _clean_cell(c)]
            if cells:
                rows.append(cells)
        return rows

def _detect_header_and_mode(rows: List[List[str]]) -> Tuple[bool, str, List[str]]:
    """
    Detect if the first row is a header and whether the CSV is:
      - single-column canonical list (e.g., header 'State' or 'Name')
      - multi-column canonical + aliases (first col canonical, rest aliases)
    Returns: (has_header, header_first_cell, first_row)
    """
    if not rows:
        return False, "", []
    first = rows[0]
    first_cell = first[0].lower()
    likely_headers = {"state", "city", "name", "canonical", "alias", "aliases"}
    has_header = first_cell in likely_headers
    return has_header, first[0], first

def _rows_to_mapping(rows: List[List[str]], single_col_ok: bool = True) -> Dict[str, str]:
    """
    Convert rows into a lowercase->canonical mapping.
    Supports:
      - Single column with or without header
      - Multi column where first column is canonical and remaining are aliases
    """
    mapping: Dict[str, str] = {}
    if not rows:
        return mapping

    has_header, _header_cell, _header_row = _detect_header_and_mode(rows)

    # If header present, drop it
    if has_header:
        rows = rows[1:]

    for r in rows:
        if not r:
            continue
        canon = _clean_cell(r[0])
        if not canon:
            continue

        # Always include canonical form
        mapping[canon.lower()] = canon

        # If multi-column: treat remaining columns as aliases
        if len(r) > 1:
            for alias in r[1:]:
                alias = _clean_cell(alias)
                if not alias:
                    continue
                # Avoid self-alias duplicates
                if alias.lower() == canon.lower():
                    continue
                mapping[alias.lower()] = canon
        else:
            # Single-column allowed (canonical only)
            if not single_col_ok:
                continue

    return mapping

def _load_generic(path: str) -> Dict[str, str]:
    """
    Load a CSV that may be either single-column (canonical only) or
    multi-column (canonical + aliases). Returns lowercase->canonical mapping.
    """
    p = Path(path)
    rows = _read_rows(p)
    return _rows_to_mapping(rows, single_col_ok=True)

# --------------------
# Public loaders
# --------------------

def load_states(base: str = "data/states.csv") -> Dict[str, str]:
    """
    Supports:
      - Single column with header like 'State' (works with your current file)
      - Multi columns with canonical + alias(es)
    """
    return _load_generic(base)

def load_cities(base: str = "data/cities.csv") -> Dict[str, str]:
    """Same flexible handling for cities; aliases are optional."""
    return _load_generic(base)

def load_names(base: str = "data/names.csv") -> Dict[str, str]:
    """Same flexible handling for names."""
    return _load_generic(base)

# --------------- Optional: quick debug ---------------

def sample_preview(mapping: Dict[str, str], n: int = 6) -> List[Tuple[str, str]]:
    """Return up to n key->value samples to help verify loads during debugging."""
    out = []
    for i, (k, v) in enumerate(mapping.items()):
        if i >= n:
            break
        out.append((k, v))
    return out
