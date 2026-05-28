import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import flet as ft
from src.main import main

if __name__ == "__main__":
    ft.app(target=main)
