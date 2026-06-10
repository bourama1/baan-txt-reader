# Baan TXT Reader

A standalone Python library for parsing Baan-generated industrial door configuration files (`tmpxxxxx.txt`).

## Features

- **Global Header Extraction**: Captures order metadata (Customer, Order Number, etc.).
- **Hierarchical Grouping**: Organizes data by `Pozice` (Position).
- **Sub-Configuration Support**: Distinctly parses items within a position (e.g., Doorleaf, Rails, Hardware).
- **ID-Based Mapping**: Maps all 8-digit characteristic IDs to their values.
- **Robust Encoding**: Automatically handles `windows-1250` encoding used by Baan.

## Installation

You can install this package directly from the company repository or local path:

```bash
# Using uv (recommended)
uv add "git+https://github.com/bourama1/baan-txt-reader.git"

# Using pip
pip install "git+https://github.com/bourama1/baan-txt-reader.git"
```

## Usage

```python
from baan_txt_reader import BaanReader

# Initialize the reader
reader = BaanReader()

# Read a Baan TXT file
data = reader.read("TMP022812498.TXT")

# 1. Get global order info
print(f"Customer: {data['header'].get('Odběratel')}")

# 2. Access a specific position
pos_10 = data["positions"].get("10")

# 3. Access characteristics of a Doorleaf in that position
if pos_10 and "Doorleaf (Indy)" in pos_10:
    doorleaf = pos_10["Doorleaf (Indy)"]
    print(f"Doorleaf ID: {doorleaf['id']}")

    # Access characteristic by its 8-digit ID
    width = doorleaf["characteristics"].get("06000020")
    print(f"Width: {width} mm")
```

## Data Structure Example

```json
{
  "header": {
    "Odběratel": "001306",
    "Zakázka": "603201"
  },
  "positions": {
    "10": {
      "Doorleaf (Indy)": {
        "id": "010-510632",
        "characteristics": {
          "06000020": "3000",
          "06000030": "3000"
        }
      }
    }
  }
}
```
