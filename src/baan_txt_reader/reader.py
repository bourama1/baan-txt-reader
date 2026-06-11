import re
from pathlib import Path
from typing import Any, Dict


class BaanReader:
    """A reader for Baan-generated TXT files (orders and quotations).

    Handles two slightly different formats:

    ORDERS (Prod.obj.)
        ID    Kont  |  <id>  |  |  <name>
        Characteristics:  10|06280001|Description|value|***

    QUOTATIONS (Prod.nabídka)
        ID          |  <id>  |  |  <name>       ← no "Kont" word
        Characteristics:   3 |  00000004 | Description  |   value |
        Some lines are wrapped in double quotes due to semicolons in values.

    Strategy
    --------
    * Global header  — all shared key|value fields, stored on first
                       occurrence only (subsequent repetitions are identical
                       and safely ignored).
    * Configurator   — stores only the two unique fields:
                         'id'       Kont / ID identifier
                         'vyr_obj'  Výr.obj. (production/quotation order number,
                                    may be empty for quotations)
                       plus 'characteristics' (the numbered attribute lines).
    * in_char_section flag — set to True when numeric characteristic lines
      begin; prevents T09 BOM rows and "Celkem" totals from leaking into
      the global header.  Reset to False on every Pozice / ID boundary.
    """

    def __init__(self):
        # Allow optional whitespace around the 8-digit ID:
        #   orders:     |06280001|
        #   quotations: |  00000004 |
        self.id_pattern = re.compile(r"\|\s*(\d{8})\s*\|")
        self.pozice_pattern = re.compile(r"^Pozice\s*\|\s*(\d+)")
        # Match both order format "ID    Kont | …" and quotation format "ID | …"
        self.sub_header_pattern = re.compile(
            r"^ID(?:\s+Kont)?\s*\|\s*([^|]+)\|\s*\|\s*([^|]+)"
        )
        # Characteristic lines start with optional spaces, an index number, then a pipe:
        #   orders:     " 10|06280001|Description|value|"
        #   quotations: "    3 |  00000004 | Description  |  value |"
        self.char_line_pattern = re.compile(r"^\s*\d+\s*\|")

    def read(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Reads a Baan TXT file and returns a structured dictionary.

        Args:
            file_path: Path to the .txt file.

        Returns:
            {
              "header": {
                  "Odběratel": "001306",
                  "Prod.obj.": "603180",
                  "Datum obj.": "28.05.2026",
                  …                              # all shared order fields
              },
              "positions": {
                  "10": {
                      "Lanko (Indy)": {
                          "id": "4*6950*04",
                          "vyr_obj": "217765",
                          "characteristics": {"06280001": "6950", …}
                      },
                      "Doorleaf (Indy)": {
                          "id": "010-510632",
                          "vyr_obj": "217751",
                          "characteristics": {"00000021": "EN", …}
                      },
                      …
                  }
              }
            }
        """
        data: Dict[str, Any] = {"header": {}, "positions": {}}

        current_position_id: str | None = None
        current_configurator: Dict | None = None
        current_characteristics: Dict | None = None
        in_char_section = False  # True once numeric characteristic lines start

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(path, "r", encoding="windows-1250", errors="replace") as f:
            for line in f:
                sanitized_line = line.strip()
                # Quotation files occasionally wrap lines in double quotes when
                # a value field contains semicolons, e.g.:
                #   "  557 |  09003015 | Ridici jednotka  |  936-010 | NG 601; XF"
                if sanitized_line.startswith('"') and sanitized_line.endswith('"'):
                    sanitized_line = sanitized_line[1:-1].strip()
                if not sanitized_line:
                    continue

                # ── 1. Pozice ────────────────────────────────────────────────
                # Position boundary.  Reset characteristic-section flag so
                # header fields that follow (before ID Kont) are processed.
                pozice_match = self.pozice_pattern.match(sanitized_line)
                if pozice_match:
                    current_position_id = pozice_match.group(1).strip()
                    if current_position_id not in data["positions"]:
                        data["positions"][current_position_id] = {}
                    current_configurator = None
                    current_characteristics = None
                    in_char_section = False
                    continue

                # ── 2. ID Kont ───────────────────────────────────────────────
                # Configurator identifier — unique per sub-item in the order.
                sub_header_match = self.sub_header_pattern.match(sanitized_line)
                if sub_header_match and current_position_id is not None:
                    item_id = sub_header_match.group(1).strip()
                    sub_header_name = sub_header_match.group(2).strip()

                    entry: Dict[str, Any] = {
                        "id": item_id,
                        "vyr_obj": None,
                        "characteristics": {},
                    }
                    data["positions"][current_position_id][sub_header_name] = entry
                    current_configurator = entry
                    current_characteristics = entry["characteristics"]
                    in_char_section = False
                    continue

                # ── 3. Characteristic line ───────────────────────────────────
                # Format:  index | 8-digit-ID | description | value | …
                if self.char_line_pattern.match(sanitized_line):
                    id_match = self.id_pattern.search(sanitized_line)
                    if id_match and current_characteristics is not None:
                        in_char_section = True
                        char_id = id_match.group(1)
                        parts = sanitized_line.split("|")
                        if len(parts) >= 4:
                            value = parts[3].strip().replace("*", "")
                            current_characteristics[char_id] = value
                    continue

                # ── 4. Header-style field  (key | value …) ──────────────────
                # Guard: once characteristics have started (in_char_section),
                # remaining pipe-delimited lines are T09 BOM rows or "Celkem"
                # totals — skip them all.  The header fields for the *next*
                # configurator block appear before its Pozice line, which will
                # flip in_char_section back to False.
                if in_char_section or "|" not in sanitized_line:
                    continue

                parts = sanitized_line.split("|")
                key = parts[0].strip()
                if not key or len(parts) < 2:
                    continue

                raw_value = parts[1].strip()

                # Výr.obj. is the one field that differs between configurators
                if key == "Výr.obj." and current_configurator is not None:
                    current_configurator["vyr_obj"] = raw_value
                    continue

                # Every other field is shared order-level data.
                # First-occurrence-wins: identical repetitions are no-ops.
                if raw_value and key not in data["header"]:
                    data["header"][key] = raw_value.replace("*", "")

        return data
