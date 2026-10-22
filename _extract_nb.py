import json
from pathlib import Path

p = Path("notebooks/Gabriel_Victalino_Mancebo_Prática_EDA.ipynb")
nb = json.loads(p.read_text(encoding="utf-8"))
out = []
for i, c in enumerate(nb["cells"]):
    src = "".join(c.get("source", []))
    out.append("=" * 80)
    out.append(f"CELL {i} [{c['cell_type']}]")
    out.append(src)
    out.append("")
Path("_nb_cells.txt").write_text("\n".join(out), encoding="utf-8")
print(f"wrote {len(nb['cells'])} cells, {Path('_nb_cells.txt').stat().st_size} bytes")
