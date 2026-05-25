import sys
import shutil
from pathlib import Path


def build():
    project_root = Path(__file__).parent
    icon_path = project_root / "assets" / "images" / "app.ico"
    dist_dir = project_root / "dist"

    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=G360-Stock-Consolidator",
        "--onedir",
        "--windowed",
        f"--icon={icon_path}" if icon_path.exists() else "",
        "--paths=.",
        "--add-data=src;src",
        "--add-data=assets;assets",
        "--add-data=reference;reference",
        "--hidden-import=flet",
        "--hidden-import=openpyxl",
        "--hidden-import=xlrd",
        "--hidden-import=pandas",
        "--hidden-import=beautifulsoup4",
        "--hidden-import=lxml",
        "run.py",
    ]

    cmd = [c for c in cmd if c]

    import subprocess
    subprocess.run(cmd, cwd=project_root)
    print(f"Build complete: {dist_dir / 'G360-Stock-Consolidator'}")


if __name__ == "__main__":
    build()
