import re
from pathlib import Path
from typing import Any


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
                       plus 'characteristics' (the numbered attribute lines)
                       and 'bom' / 'bom_total_weight' (the material rows that
                       follow a configurator's characteristics, and their
                       "Celkem Hmotnost" total, e.g.:
                         " T09-010-29-0022|  31,8500|m1 |Hmotnost  | 587,537  528502"
                         "Celkem  Hmotnost  |    993,857"
                       ).
    * in_char_section flag — set to True when numeric characteristic lines
      begin; prevents T09 BOM rows and "Celkem" totals from leaking into
      the global header.  Reset to False on every Pozice / ID boundary.
    """

    def __init__(self):
        self.pozice_pattern = re.compile(r"^Pozice\s*\|\s*(\d+)")
        # Match both order format "ID    Kont | …" and quotation format "ID | …"
        self.sub_header_pattern = re.compile(
            r"^ID(?:\s+Kont)?\s*\|\s*([^|]+)\|\s*\|\s*([^|]+)"
        )
        # Characteristic lines start with optional spaces, an index number, then a pipe:
        #   orders:     " 10|06280001|Description|value|"
        #   quotations: "    3 |  00000004 | Description  |  value |"
        self.char_line_pattern = re.compile(r"^\s*\d+\s*\|")

        # BOM (bill of materials) lines follow a configurator's characteristics.
        # Unlike characteristic lines, they start with a material code instead
        # of a numeric index, e.g.:
        #   " T09-010-29-0022|      31,8500|m1 |Hmotnost  |    587,537     528502"
        #   "    FV_254211_10|       1,0000|pcs|Hmotnost  |      0,000     528502"
        # Fields: <code> | <qty> | <unit> | "Hmotnost" | <weight>  <variant>
        self.bom_line_pattern = re.compile(
            r"^\s*(?P<code>\S+)\s*\|\s*(?P<qty>[\d.,]+)\s*\|\s*(?P<unit>\S*)\s*\|"
            r"\s*Hmotnost\s*\|\s*(?P<weight>[\d.,]+)\s+(?P<variant>\S+)\s*$"
        )
        # Closes out a configurator's BOM section, e.g. "Celkem  Hmotnost  |    993,857"
        self.bom_total_pattern = re.compile(
            r"^Celkem\s+Hmotnost\s*\|\s*(?P<total>[\d.,]+)\s*$"
        )

    def read(self, file_path: str | Path) -> dict[str, Any]:
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
                          "characteristics": {"06280001": "6950", …},
                          "bom": [
                              {"code": "T09-010-29-0022", "qty": "31,8500",
                               "unit": "m1", "weight": "587,537", "variant": "528502"},
                              …
                          ],
                          "bom_total_weight": "993,857"
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
        data: dict[str, Any] = {"header": {}, "positions": {}}

        current_position_id: str | None = None
        current_configurator: dict | None = None
        current_characteristics: dict | None = None
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

                    entry: dict[str, Any] = {
                        "id": item_id,
                        "vyr_obj": None,
                        "characteristics": {},
                        "bom": [],
                        "bom_total_weight": None,
                    }
                    data["positions"][current_position_id][sub_header_name] = entry
                    current_configurator = entry
                    current_characteristics = entry["characteristics"]
                    in_char_section = False
                    continue

                # ── 3. Characteristic line ───────────────────────────────────
                # Format:  index | ID | description | value | …
                #
                # The ID field is normally an 8-digit BaaN code (e.g.
                # "06280001"), but some door variants (e.g. GT-R) use short
                # alphanumeric codes instead, right-padded with spaces to the
                # same 8-character field width, e.g. "    SLPP", "    ApUp".
                # Rather than requiring 8 digits, we take the ID directly
                # from the second pipe-delimited field so both forms work.
                if self.char_line_pattern.match(sanitized_line):
                    parts = sanitized_line.split("|")
                    if len(parts) >= 4 and current_characteristics is not None:
                        in_char_section = True
                        char_id = parts[1].strip()
                        if char_id:
                            value = parts[3].strip().replace("*", "")
                            current_characteristics[char_id] = value
                    continue

                # ── 3b. BOM (bill of materials) line ─────────────────────────
                # Comes after a configurator's characteristics, one row per
                # consumed material. Keep in_char_section True so the header
                # guard below doesn't misfile these into data["header"].
                bom_match = self.bom_line_pattern.match(sanitized_line)
                if bom_match and current_configurator is not None:
                    in_char_section = True
                    current_configurator["bom"].append(
                        {
                            "code": bom_match.group("code"),
                            "qty": bom_match.group("qty"),
                            "unit": bom_match.group("unit"),
                            "weight": bom_match.group("weight"),
                            "variant": bom_match.group("variant"),
                        }
                    )
                    continue

                # ── 3c. BOM total  ("Celkem  Hmotnost | <total>") ────────────
                # Marks the end of the current configurator's BOM section.
                total_match = self.bom_total_pattern.match(sanitized_line)
                if total_match and current_configurator is not None:
                    current_configurator["bom_total_weight"] = total_match.group(
                        "total"
                    )
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
