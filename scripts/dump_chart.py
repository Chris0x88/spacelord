import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent
sys.path.append(str(root_dir))

from src.plugins.power_law.charting import generate_powerlaw_png

png_bytes = generate_powerlaw_png()
with open("desktop_chart.png", "wb") as f:
    f.write(png_bytes)
print("Saved to desktop_chart.png")
