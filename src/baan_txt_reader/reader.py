import re
from pathlib import Path
from typing import Any, Dict


class BaanReader:
    """A reader for Baan-generated TXT files."""

    def __init__(self):
        self.id_pattern = re.compile(r"\|(\d{8})\|")
        self.pozice_pattern = re.compile(r"^Pozice\s*\|\s*(\d+)")
        self.sub_header_pattern = re.compile(
            r"^ID\s+Kont\s*\|\s*([^|]+)\|\s*\|\s*([^|]+)"
        )

    def read(self, file_path: str | Path) -> Dict[str, Any]:
        """
        Reads a Baan TXT file and returns a structured dictionary.

        Args:
            file_path: Path to the .txt file.

        Returns:
            A dictionary with 'header' and 'positions'.
        """
        data = {"header": {}, "positions": {}}

        current_position_id = None
        current_characteristics = None

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Use windows-1250 encoding as specified in requirements
        with open(path, "r", encoding="windows-1250", errors="replace") as f:
            for line in f:
                sanitized_line = line.strip()
                if not sanitized_line:
                    continue

                # 1. Global Header Parsing (before any position is found)
                if current_position_id is None:
                    # Check if this line is a Pozice line
                    pozice_match = self.pozice_pattern.match(sanitized_line)
                    if pozice_match:
                        current_position_id = pozice_match.group(1).strip()
                        data["positions"][current_position_id] = {}
                    else:
                        # Extract header fields (Odběratel, Zakázka, etc.)
                        if "|" in sanitized_line:
                            parts = sanitized_line.split("|")
                            key = parts[0].strip()
                            if key and len(parts) > 1:
                                value = parts[1].strip().replace("*", "")
                                if value:
                                    data["header"][key] = value
                    continue

                # 2. Position Tracking
                pozice_match = self.pozice_pattern.match(sanitized_line)
                if pozice_match:
                    current_position_id = pozice_match.group(1).strip()
                    if current_position_id not in data["positions"]:
                        data["positions"][current_position_id] = {}
                    current_characteristics = None
                    continue

                # 3. Sub-Header Parsing (ID Kont lines)
                sub_header_match = self.sub_header_pattern.match(sanitized_line)
                if sub_header_match:
                    item_id = sub_header_match.group(1).strip()
                    sub_header_name = sub_header_match.group(2).strip()

                    data["positions"][current_position_id][sub_header_name] = {
                        "id": item_id,
                        "characteristics": {},
                    }
                    current_characteristics = data["positions"][current_position_id][
                        sub_header_name
                    ]["characteristics"]
                    continue

                # 4. Characteristic Extraction (8-digit IDs)
                id_match = self.id_pattern.search(sanitized_line)
                if id_match and current_characteristics is not None:
                    char_id = id_match.group(1)
                    # The value is in the next column after the ID
                    parts = sanitized_line.split("|")
                    # Pattern is usually: index | ID | Description | Value | ...
                    # We want the part after the description (which is after the ID)
                    if len(parts) >= 4:
                        value = parts[3].strip().replace("*", "")
                        current_characteristics[char_id] = value

        return data
