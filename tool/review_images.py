#!/usr/bin/env python3
"""Render detection and panoptic annotations for human review."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("Cần Pillow: python3 -m pip install Pillow")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def candidates(path: Path) -> dict[str, list[str]]:
    data = read_json(path)
    if isinstance(data, dict):
        data = data.get("candidates", data.get("errors"))
    if not isinstance(data, list):
        raise ValueError("Candidates phải là danh sách hoặc object có khóa candidates/errors")
    result: dict[str, list[str]] = {}
    for entry in data:
        if not isinstance(entry, dict):
            raise ValueError("Mỗi ứng viên phải là object có image hoặc target")
        name = entry.get("image", entry.get("target"))
        if not isinstance(name, str):
            raise ValueError("Ứng viên thiếu image hoặc target")
        name = Path(name).stem
        result.setdefault(name, []).append(str(entry.get("type", "chưa ghi loại")))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("delivery", type=Path, help="Thư mục delivery")
    parser.add_argument("--out", type=Path, required=True, help="Thư mục xuất trang review")
    parser.add_argument("--image", action="append", default=[], help="Tên ảnh cần xem; có thể truyền nhiều lần")
    parser.add_argument("--candidates", type=Path, help="JSON danh sách ứng viên")
    args = parser.parse_args()
    root = args.delivery
    manifest = read_json(root / "manifest.json")["items"]
    panoptic = read_json(root / "panoptic.json")
    categories = {x["id"]: x for x in panoptic["categories"]}
    annotations = {Path(x["file_name"]).stem: x for x in panoptic["annotations"]}
    classes = {}
    for line in (root / "classes.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            number, name = line.split(maxsplit=1)
            classes[int(number)] = name
    queue = candidates(args.candidates) if args.candidates else {}
    selected = {Path(name).stem for name in args.image}
    if args.candidates:
        selected.update(queue)
    if not args.image and not args.candidates:
        selected = set(manifest)
    unknown = selected - manifest.keys()
    if unknown:
        parser.error("Ảnh không có trong manifest: " + ", ".join(sorted(unknown)))
    if args.out.resolve().is_relative_to(root.resolve()):
        parser.error("Thư mục xuất phải nằm ngoài delivery để giữ nguyên dữ liệu gốc")
    args.out.mkdir(parents=True, exist_ok=True)
    assets = args.out / "assets"
    assets.mkdir(exist_ok=True)
    cards = []
    for index, name in enumerate(sorted(selected)):
        item = manifest[name]
        path = root / item["image"]
        if not path.is_file():
            print(f"Bỏ qua ảnh thiếu: {name}", file=sys.stderr)
            continue
        try:
            image = Image.open(path).convert("RGB")
            image.load()
            width, height = image.size
            drawing = Image.new("RGBA", image.size)
            draw = ImageDraw.Draw(drawing)
            label_path = root / item["label"]
            labels = []
            warnings = []
            if label_path.is_file():
                for i, line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), 1):
                    if not line.strip():
                        continue
                    try:
                        cls, x, y, w, h = map(float, line.split())
                        if not all(map(math.isfinite, (cls, x, y, w, h))) or w <= 0 or h <= 0 or not cls.is_integer():
                            raise ValueError("class hoặc tọa độ không hợp lệ")
                    except ValueError:
                        warnings.append(f"Dòng detection {i} không hợp lệ: {line}")
                        continue
                    title = f"D{i}: {classes.get(int(cls), f'class {cls:g}')}"
                    labels.append(title)
                    box = ((x-w/2)*width, (y-h/2)*height, (x+w/2)*width, (y+h/2)*height)
                    draw.rectangle(box, outline="#ff3333", width=3)
                    draw.text((box[0]+2, max(0, box[1]-12)), title, fill="white", stroke_width=2, stroke_fill="black")
            else:
                warnings.append("Không tìm thấy file nhãn detection")
            annotation = annotations.get(Path(item["mask"]).stem)
            mask_path = root / item["mask"]
            mask = None
            segments = []
            boundaries = Image.new("RGBA", image.size)
            if annotation and mask_path.is_file():
                try:
                    mask = Image.open(mask_path).convert("RGB")
                    mask.load()
                    if mask.size != image.size:
                        raise ValueError(f"Kích thước mask {mask.size} khác ảnh {image.size}")
                except (OSError, ValueError) as exc:
                    warnings.append(f"Không thể hiển thị mask: {exc}")
                    mask = None
            else:
                warnings.append("Không tìm thấy mask hoặc annotation panoptic")
            if mask is not None:
                thing_ids = set()
                segment_labels = []
                for n, segment in enumerate(annotation["segments_info"], 1):
                    cat = categories.get(segment["category_id"], {})
                    if cat.get("isthing") or not cat:
                        thing_ids.add(segment["id"])
                        category_name = cat.get('name', f"category không hợp lệ {segment['category_id']}")
                        segments.append(f"P{n}: {category_name} (id {segment['id']}, crowd={segment.get('iscrowd', 0)})")
                        x, y, w, h = segment["bbox"]
                        segment_labels.append((x, y, f"P{n}"))
                raw = mask.tobytes()
                ids = [raw[i] + (raw[i+1] << 8) + (raw[i+2] << 16) for i in range(0, len(raw), 3)]
                edge = bytearray(width * height)
                for pos, segment_id in enumerate(ids):
                    if segment_id not in thing_ids:
                        continue
                    x, y = pos % width, pos // width
                    if (x == 0 or y == 0 or x == width - 1 or y == height - 1
                            or ids[pos-1] != segment_id or ids[pos+1] != segment_id
                            or ids[pos-width] != segment_id or ids[pos+width] != segment_id):
                        edge[pos] = 255
                from PIL import ImageFilter
                edge_mask = Image.frombytes("L", image.size, bytes(edge)).filter(ImageFilter.MaxFilter(3))
                boundaries.paste((0, 255, 255, 255), (0, 0, width, height), edge_mask)
                segment_draw = ImageDraw.Draw(boundaries)
                for x, y, title in segment_labels:
                    segment_draw.text((x + 2, y + 2), title, fill="cyan", stroke_width=2, stroke_fill="black")
            image.save(assets / f"{index}_original.png")
            drawing.save(assets / f"{index}_boxes.png")
            boundaries.save(assets / f"{index}_edges.png")
            cards.append({"name": name, "index": index, "width": width, "height": height, "labels": labels, "segments": segments, "warnings": warnings, "types": queue.get(name, [])})
        except (OSError, ValueError) as exc:
            print(f"Không xử lý được {name}: {exc}", file=sys.stderr)
    data = json.dumps(cards, ensure_ascii=False).replace("<", "\\u003c")
    (args.out / "catalog.json").write_text(json.dumps(cards, ensure_ascii=False), encoding="utf-8")
    page = (Path(__file__).parent / "review.html").read_text(encoding="utf-8").replace("__REVIEW_DATA__", data)
    (args.out / "index.html").write_text(page, encoding="utf-8")
    print(f"Đã tạo {len(cards)} ảnh review: {args.out / 'index.html'}")


if __name__ == "__main__":
    main()
