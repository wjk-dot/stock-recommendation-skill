import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pack_recommendations import pack  # noqa: E402
from render_gui import render  # noqa: E402
from text_io import ensure_text_is_not_garbled, load_json_bytes, write_utf8  # noqa: E402


class EncodingTests(unittest.TestCase):
    def test_loads_gbk_json_from_upstream(self) -> None:
        payload = [{"code": "000001", "name": "平安银行"}]
        data = json.dumps(payload, ensure_ascii=False).encode("gb18030")
        self.assertEqual(load_json_bytes(data)[0]["name"], "平安银行")

    def test_loads_utf8_bom_json(self) -> None:
        data = b"\xef\xbb\xbf" + json.dumps({"name": "中国平安"}, ensure_ascii=False).encode("utf-8")
        self.assertEqual(load_json_bytes(data)["name"], "中国平安")

    def test_rejects_lost_characters(self) -> None:
        with self.assertRaises(ValueError):
            ensure_text_is_not_garbled({"name": "平锟斤拷锟斤拷"})
        with self.assertRaises(ValueError):
            ensure_text_is_not_garbled({"name": "����"})

    def test_pack_keeps_clean_name(self) -> None:
        result = pack(
            [{
                "code": "000001",
                "name": "平安银行",
                "realtime": {"name": "平安银行", "price": 10, "pre_close": 9.9},
            }],
            {},
        )
        self.assertEqual(result["stocks"][0]["name"], "平安银行")

    def test_render_rejects_garbled_name(self) -> None:
        with self.assertRaises(ValueError):
            render({"stocks": [{"code": "000001", "name": "����"}]}, "__DATA_JSON__")

    def test_write_is_utf8_without_bom(self) -> None:
        path = ROOT / "tests" / "_encoding_output.json"
        try:
            write_utf8(path, '{"name":"平安银行"}')
            self.assertEqual(path.read_bytes(), '{"name":"平安银行"}'.encode("utf-8"))
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
