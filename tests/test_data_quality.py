import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "data_quality.py"


def test_script_reports_known_findings():
    out = subprocess.run([sys.executable, "-W", "ignore", SCRIPT], capture_output=True, text=True,
                         encoding="utf-8", check=True).stdout
    assert out.startswith("## Data quality findings")
    for expected in ("order 8", "product 136", "product 130", "product 96", "customers 11, 43"):
        assert expected in out
