# debug.py
from pathlib import Path

BASE_DIR = Path("C:\\Users\\uwaif\\guan_platform")
templates_dir = BASE_DIR / "templates"

print(f"Templates directory exists: {templates_dir.exists()}")
if templates_dir.exists():
    print(f"Files in templates directory:")
    for file in templates_dir.iterdir():
        print(f"  - {file.name}")
        print(f"    Is file: {file.is_file()}")
        print(f"    Size: {file.stat().st_size if file.is_file() else 'N/A'}")