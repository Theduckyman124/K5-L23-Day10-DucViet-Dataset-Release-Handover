#!/usr/bin/env python3
"""Công cụ vẽ Bounding Box (YOLO Detection) và Panoptic Segment lên ảnh để Review mắt thường."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def visualize(delivery_dir: Path, image_name: str, out_path: Path):
    img_path = delivery_dir / "images" / f"{image_name}.jpg"
    lbl_path = delivery_dir / "labels" / f"{image_name}.txt"
    pan_path = delivery_dir / "panoptic.json"
    cls_path = delivery_dir / "classes.txt"

    if not img_path.is_file():
        print(f"Không tìm thấy ảnh: {img_path}")
        return

    img = Image.open(img_path).convert("RGB")
    W, H = img.size
    draw = ImageDraw.Draw(img)

    # 1. Đọc tên lớp YOLO
    classes = {}
    if cls_path.is_file():
        for line in cls_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cid, name = line.split(maxsplit=1)
                classes[int(cid)] = name.strip()

    # 2. Đọc Panoptic Segment
    panoptic = json.loads(pan_path.read_text(encoding="utf-8"))
    things = {c["id"]: c["name"] for c in panoptic["categories"] if c.get("isthing")}
    ann_map = {Path(a["file_name"]).stem: a for a in panoptic["annotations"]}
    ann = ann_map.get(image_name)

    if ann:
        for s in ann.get("segments_info", []):
            if s.get("category_id") in things and not s.get("iscrowd"):
                sx, sy, sw, sh = s["bbox"]
                cat_name = things[s["category_id"]]
                # Vẽ viền nét đứt hoặc màu tím cho Panoptic Segment
                draw.rectangle([sx, sy, sx + sw, sy + sh], outline="magenta", width=2)
                draw.text((sx + 3, sy + 3), f"Pan: {cat_name} ({s['area']}px)", fill="magenta")

    # 3. Đọc và vẽ Detection Box (màu xanh lá/đỏ)
    if lbl_path.is_file():
        for line in lbl_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            parts = line.split()
            cid = int(float(parts[0]))
            x, y, w, h = map(float, parts[1:5])
            x1 = (x - w / 2) * W
            y1 = (y - h / 2) * H
            x2 = (x + w / 2) * W
            y2 = (y + h / 2) * H
            cname = classes.get(cid, str(cid))
            # Vẽ hộp Detection
            draw.rectangle([x1, y1, x2, y2], outline="cyan", width=3)
            draw.text((x1 + 3, y1 + 3), f"Det: {cname}", fill="cyan")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    print(f"Đã vẽ và lưu ảnh trực quan tại: {out_path}")

def main():
    parser = argparse.ArgumentParser(description="Vẽ box và segment lên ảnh để review")
    parser.add_argument("--delivery", type=Path, default=Path("runs/r3007/delivery"))
    parser.add_argument("--candidates", type=Path, default=Path("runs/r3007/candidates.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("runs/r3007/visualized"))
    parser.add_argument("--image", type=str, help="Vẽ riêng một ảnh")
    args = parser.parse_args()

    if args.image:
        visualize(args.delivery, args.image, args.out_dir / f"{args.image}_vis.jpg")
    elif args.candidates.is_file():
        doc = json.loads(args.candidates.read_text(encoding="utf-8"))
        images = sorted(list({c["image"] for c in doc.get("candidates", [])}))
        print(f"Đang vẽ {len(images)} ảnh ứng viên vào {args.out_dir}...")
        for img_name in images:
            visualize(args.delivery, img_name, args.out_dir / f"{img_name}_vis.jpg")
        print("Hoàn thành!")

if __name__ == "__main__":
    main()
