# tests/test_spreadsheet_tools.py
import tempfile, unittest
from pathlib import Path
from permissions import PermissionGate
from tools.spreadsheet import make_spreadsheet_tools

def _tools(root: Path):
    gate = PermissionGate(root, (), lambda m: True, lambda m: True)
    return {t.name: t for t in make_spreadsheet_tools(gate)}

class TestSheetTools(unittest.TestCase):
    def test_write_read_cell(self):
        with tempfile.TemporaryDirectory() as d:
            t = _tools(Path(d))
            t["sheet_write_cell"].func({"path": "book.xlsx", "sheet": "Sheet1", "cell": "A1", "value": "42"})
            out = t["sheet_read"].func({"path": "book.xlsx", "sheet": "Sheet1"})
            self.assertIn("42", out)

    def test_summary(self):
        with tempfile.TemporaryDirectory() as d:
            t = _tools(Path(d))
            t["sheet_write_cell"].func({"path": "book.xlsx", "sheet": "Sheet1", "cell": "A1", "value": "name"})
            out = t["sheet_summary"].func({"path": "book.xlsx"})
            self.assertIn("Sheet1", out)

if __name__ == "__main__":
    unittest.main()
