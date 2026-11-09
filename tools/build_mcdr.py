import json
import pathlib
import zipfile

root = pathlib.Path(__file__).resolve().parents[1]
manifest = json.loads((root / "mcdreforged.plugin.json").read_text(encoding="utf-8"))
version = manifest.get("version", "0.0.0")
out = root / "dist" / f"nsum_bridge-{version}.mcdr"
out.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
    archive.write(root / "mcdreforged.plugin.json", "mcdreforged.plugin.json")
    for path in sorted((root / "nsum_bridge").rglob("*.py")):
        archive.write(path, str(path.relative_to(root)))
print(out, out.stat().st_size)
