"""Local review server: dataset assets, persistent uploads and review notes."""
import argparse
import base64
import csv
import io
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit
from uuid import uuid4

from PIL import Image

HERE = Path(__file__).resolve().parent


def read(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def handler(root):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, body, content_type="application/json"):
            if content_type == "application/json":
                body = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/api/images":
                return self.reply(200, read(root / "catalog.json", []) + read(root / "uploads.json", []))
            if path == "/api/reviews":
                return self.reply(200, read(root / "reviews.json", []))
            if path == "/api/reviews.csv":
                buffer = io.StringIO(newline="")
                writer = csv.DictWriter(buffer, fieldnames=["image", "type", "verdict", "note"])
                writer.writeheader()
                writer.writerows(read(root / "reviews.json", []))
                return self.reply(200, buffer.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8")
            if path in ("/", "/index.html"):
                page = (HERE / "review.html").read_text(encoding="utf-8").replace("__REVIEW_DATA__", "[]")
                return self.reply(200, page.encode(), "text/html; charset=utf-8")
            if path.startswith("/assets/"):
                asset = (root / path.lstrip("/")).resolve()
                if asset.is_relative_to((root / "assets").resolve()) and asset.is_file() and asset.suffix == ".png":
                    return self.reply(200, asset.read_bytes(), "image/png")
            self.reply(404, {"error": "Không tìm thấy tài nguyên"})

        def do_POST(self):
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + self.headers.get("Host", ""):
                return self.reply(403, {"error": "Origin không hợp lệ"})
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 28_000_000:
                    return self.reply(413, {"error": "Giới hạn ảnh tải lên: 20 MB"})
                data = json.loads(self.rfile.read(length))
                if self.path == "/api/upload":
                    content = base64.b64decode(data["data"], validate=True)
                    with Image.open(io.BytesIO(content)) as source:
                        if source.width * source.height > 25_000_000:
                            raise ValueError("Ảnh vượt quá 25 triệu pixel")
                        image = source.convert("RGB")
                    key = "upload_" + uuid4().hex
                    image.save(root / "assets" / f"{key}_original.png")
                    overlay = Image.new("RGBA", image.size)
                    for layer in ("boxes", "edges"):
                        overlay.save(root / "assets" / f"{key}_{layer}.png")
                    item = dict(name=Path(data["name"]).name, index=key, width=image.width, height=image.height,
                                labels=[], segments=[], types=[], warnings=["Ảnh tải lên chưa có nhãn detection hoặc panoptic."])
                    uploads = read(root / "uploads.json", [])
                    uploads.append(item)
                    save(root / "uploads.json", uploads)
                    return self.reply(201, item)
                if self.path == "/api/reviews":
                    allowed = {"class_swap", "category_swap", "bbox_drift", "missing_box", "instance_merge"}
                    names = {x["name"] for x in read(root / "catalog.json", [])}
                    if data["image"] not in names:
                        raise ValueError("Chỉ ghi review của ảnh trong delivery")
                    if data["type"] not in allowed or data["verdict"] not in ("confirmed", "rejected"):
                        raise ValueError("Loại lỗi hoặc kết luận không hợp lệ")
                    if not data["reviewer"].strip() or len(data["note"].strip()) < 20:
                        raise ValueError("Điền người xem và ghi chú ít nhất 20 ký tự")
                    row = {k: data[k] for k in ("image", "type", "verdict")}
                    row["note"] = data["reviewer"].strip() + ": " + data["note"].strip()
                    rows = read(root / "reviews.json", [])
                    rows = [r for r in rows if (r["image"], r["type"]) != (row["image"], row["type"])]
                    rows.append(row)
                    save(root / "reviews.json", rows)
                    return self.reply(200, row)
                self.reply(404, {"error": "API không tồn tại"})
            except (ValueError, KeyError, TypeError, OSError) as exc:
                self.reply(400, {"error": str(exc)})

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delivery", type=Path, default=HERE.parent / "runs/r3007/delivery")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    root = args.delivery.resolve().parent / "review_app"
    root.mkdir(parents=True, exist_ok=True)
    if args.rebuild or not (root / "catalog.json").exists():
        print("Chuẩn bị ảnh và lớp nhãn, vui lòng chờ…", flush=True)
        subprocess.run([sys.executable, str(HERE / "review_images.py"), str(args.delivery), "--out", str(root)], check=True)
    with HTTPServer(("127.0.0.1", args.port), handler(root)) as server:
        print(f"Mở http://127.0.0.1:{args.port} — Ctrl+C để dừng", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
