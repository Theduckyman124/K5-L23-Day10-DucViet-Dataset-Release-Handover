"""Exercise the reviewer on a small delivery with imperfect labels."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image


class ReviewToolTest(unittest.TestCase):
    def test_edges_warnings_and_original_delivery(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            delivery = base / "delivery"
            delivery.mkdir()
            Image.new("RGB", (10, 10), "white").save(delivery / "a.png")
            mask = Image.new("RGB", (10, 10))
            for y in range(2, 8):
                for x in range(2, 8):
                    mask.putpixel((x, y), (1, 0, 0))
            mask.save(delivery / "mask.png")
            (delivery / "label.txt").write_text("0 0.5 0.5 0.6 0.6\nbad row\n")
            (delivery / "classes.txt").write_text("0 person\n")
            (delivery / "manifest.json").write_text(json.dumps({"items": {"a": {"image": "a.png", "label": "label.txt", "mask": "mask.png"}}}))
            (delivery / "panoptic.json").write_text(json.dumps({"categories": [{"id": 1, "name": "person", "isthing": 1}], "annotations": [{"file_name": "mask.png", "segments_info": [{"id": 1, "category_id": 1, "bbox": [2, 2, 6, 6]}]}]}))
            output = base / "out"
            tool = Path(__file__).resolve().parents[1] / "tool" / "review_images.py"
            subprocess.run([sys.executable, str(tool), str(delivery), "--out", str(output)], check=True, capture_output=True, text=True)
            page = (output / "index.html").read_text()
            self.assertIn("Dòng detection 2 không hợp lệ", page)
            self.assertIn("P1: person", page)
            self.assertGreater(Image.open(output / "assets/0_edges.png").getchannel("A").getbbox()[2], 0)
            self.assertEqual((delivery / "label.txt").read_text(), "0 0.5 0.5 0.6 0.6\nbad row\n")
            inside = subprocess.run([sys.executable, str(tool), str(delivery), "--out", str(delivery / "output")], capture_output=True, text=True)
            self.assertNotEqual(inside.returncode, 0)
            self.assertFalse((delivery / "output").exists())


if __name__ == "__main__":
    unittest.main()
