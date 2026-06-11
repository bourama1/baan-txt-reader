from pprint import pprint

from baan_txt_reader import BaanReader

reader = BaanReader()

data = reader.read(
    "\\\\TOCZ-FS2\\510-TOCZ\\300 Departments\\300 Technical Services\\Dokumentace B\\NACTENO\\TMP022812498.TXT"
)
data_nabidka = reader.read(
    "\\\\TOCZ-FS2\\510-TOCZ\\300 Departments\\300 Technical Services\\Dokumentace B\\NACTENO\\TMP064041837.TXT"
)

# ── Order header ──────────────────────────────────────────────────────────────

print("=" * 60)
print("ORDER HEADER")
print("=" * 60)
pprint(data.get("header", {}))

# ── Configurators for position 10 ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("POSITION 10 — CONFIGURATORS")
print("=" * 60)

for name, cfg in data.get("positions", {}).get("10", {}).items():
    print(f"\n  {name}")
    print(f"    ID      : {cfg.get('id')}")
    print(f"    Výr.obj.: {cfg.get('vyr_obj')}")
    print("    First 10 characteristics:")
    chars = cfg.get("characteristics", {})
    for char_id, value in list(chars.items())[:10]:
        print(f"      {char_id} : {value}")

# ── Quotation header ──────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("QUOTATION HEADER")
print("=" * 60)
pprint(data_nabidka.get("header", {}))

# ── Configurators for position 10 ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("POSITION 10 — CONFIGURATORS")
print("=" * 60)

for name, cfg in data_nabidka.get("positions", {}).get("10", {}).items():
    print(f"\n  {name}")
    print(f"    ID      : {cfg.get('id')}")
    print(f"    Výr.obj.: {cfg.get('vyr_obj')}")
    print("    First 10 characteristics:")
    chars = cfg.get("characteristics", {})
    for char_id, value in list(chars.items())[:10]:
        print(f"      {char_id} : {value}")
