# Baan TXT Reader

A standalone Python library for parsing Baan-generated industrial door configuration files (`tmpxxxxx.txt`).

## Features

- **Global Header Extraction**: Captures order metadata (Customer, Order Number, etc.).
- **Hierarchical Grouping**: Organizes data by `Pozice` (Position).
- **Sub-Configuration Support**: Distinctly parses items within a position (e.g., Doorleaf, Rails, Hardware).
- **ID-Based Mapping**: Maps all characteristic IDs to their values. Handles both the standard 8-digit BaaN codes (e.g. `06280001`) and the short alphanumeric codes used by some door variants such as GT-R (e.g. `SLPP`, `ApUp`).
- **BOM Extraction**: Captures the bill-of-materials rows that follow a configurator's characteristics (material code, quantity, unit, weight, variant), plus the configurator's total weight.
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
data = reader.read(
    "\\\\TOCZ-FS2\\510-TOCZ\\300 Departments\\300 Technical Services\\Dokumentace B\\NACTENO\\TMP022812498.TXT"
)

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

    # 4. Access the BOM (bill of materials) for that configurator
    for item in doorleaf["bom"]:
        print(f"  {item['code']}: {item['qty']} {item['unit']} ({item['weight']} kg)")
    print(f"Total weight: {doorleaf['bom_total_weight']} kg")
```

## Data Structure Example

Given a raw file section like:

```
ID    Kont              |      010-528502|   |Doorleaf (Indy)
...
 10|06000020|Šířka (mm)                    |    3000|*************************
 20|06000030|Výška (mm)                    |    3000|*************************
 T09-010-29-0022|      31,8500|m1 |Hmotnost  |    587,537     528502
 T09-010-60-0181|       1,0000|pcs|Hmotnost  |      0,530     528502
Celkem  Hmotnost  |    993,857
```

`reader.read(...)` returns:

```json
{
  "header": {
    "Odběratel": "001306",
    "Zakázka": "603201"
  },
  "positions": {
    "10": {
      "Doorleaf (Indy)": {
        "id": "010-528502",
        "vyr_obj": "217751",
        "characteristics": {
          "06000020": "3000",
          "06000030": "3000"
        },
        "bom": [
          {
            "code": "T09-010-29-0022",
            "qty": "31,8500",
            "unit": "m1",
            "weight": "587,537",
            "variant": "528502"
          },
          {
            "code": "T09-010-60-0181",
            "qty": "1,0000",
            "unit": "pcs",
            "weight": "0,530",
            "variant": "528502"
          }
        ],
        "bom_total_weight": "993,857"
      }
    }
  }
}
```
