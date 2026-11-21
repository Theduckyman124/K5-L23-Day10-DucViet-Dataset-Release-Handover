import hashlib
from pathlib import Path
import tempfile
import unittest

from validator.validate import check_files, sha256_file


class FileRulesTest(unittest.TestCase):
    def test_binary_hash_missing_file_and_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = b"\xff\x00\r\n" * 300000
            item = {}
            for kind in ("image", "label", "mask"):
                (root / kind).write_bytes(payload)
                item[kind] = kind
                item[kind + "_sha256"] = hashlib.sha256(payload).hexdigest()
            manifest = {"sample": item}
            self.assertEqual(sha256_file(root / "image"), hashlib.sha256(payload).hexdigest())
            self.assertEqual(check_files(root, manifest), set())
            item["image_sha256"] = "0" * 64
            self.assertEqual(check_files(root, manifest), {("wrong_hash", "sample")})
            (root / "image").unlink()
            self.assertEqual(check_files(root, manifest), {("missing_image", "sample")})
            (root / "label").write_bytes(b"changed")
            (root / "mask").write_bytes(b"changed")
            self.assertEqual(check_files(root, manifest), {("missing_image", "sample"), ("wrong_hash", "sample")})


if __name__ == "__main__":
    unittest.main()
