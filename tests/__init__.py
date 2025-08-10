import os

from pathlib import Path

# this is being done via pyproject ini
# sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

os.environ["ENVIRONMENT"] = "TESTING"
