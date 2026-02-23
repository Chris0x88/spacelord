import sys
import os

# Add the project root to sys.path so we can import 'src' modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tui.app import PacmanTUI

def main():
    """Run the PACTUI Dashboard."""
    app = PacmanTUI()
    app.run()

if __name__ == "__main__":
    main()
