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

    def test_summary_infers_column_types(self):
        with tempfile.TemporaryDirectory() as d:
            t = _tools(Path(d))
            t["sheet_write_cell"].func({"path": "book.xlsx", "sheet": "Sheet1", "cell": "A1", "value": "名称"})
            t["sheet_write_cell"].func({"path": "book.xlsx", "sheet": "Sheet1", "cell": "B1", "value": "价格"})
            t["sheet_add_row"].func({"path": "book.xlsx", "sheet": "Sheet1", "row": ["苹果", "3.5"]})
            t["sheet_add_row"].func({"path": "book.xlsx", "sheet": "Sheet1", "row": ["香蕉", "2"]})
            out = t["sheet_summary"].func({"path": "book.xlsx"})
            self.assertIn("名称(str)", out)
            self.assertIn("价格(float)", out)

    def test_spreadsheet_overwrite_requires_strong_confirm(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            gate = PermissionGate(root, (), lambda m: True, lambda m: False)
            t = {tool.name: tool for tool in make_spreadsheet_tools(gate)}
            self.assertIn("已写入", t["sheet_write_cell"].func(
                {"path": "b.xlsx", "sheet": "Sheet1", "cell": "A1", "value": "x"}))
            out = t["sheet_write_cell"].func(
                {"path": "b.xlsx", "sheet": "Sheet1", "cell": "A1", "value": "y"})
            self.assertIn("拒绝", out)
            out2 = t["sheet_add_row"].func({"path": "b.xlsx", "sheet": "Sheet1", "row": ["z"]})
            self.assertIn("拒绝", out2)

    def test_sheet_list_filters_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "credentials.csv").write_text("a,b\n1,2", encoding="utf-8")
            t = _tools(root)
            t["sheet_write_cell"].func({"path": "ok.xlsx", "sheet": "Sheet1", "cell": "A1", "value": "x"})
            out = t["sheet_list"].func({})
            self.assertIn("ok.xlsx", out)
            self.assertNotIn("credentials", out)

if __name__ == "__main__":
    unittest.main()
