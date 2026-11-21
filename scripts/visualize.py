#!/usr/bin/env python3
"""Công cụ của Thành viên 4: Vẽ Bounding Box (YOLO) + Panoptic Segment lên ảnh, chia 6 phần review_part1..6.csv và gộp review_log.csv."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from PIL import Image, ImageDraw


def visualize(delivery_dir: Path, image_name: str, out_path: Path) -> None:
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

    classes = {}
    if cls_path.is_file():
        for line in cls_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cid, name = line.split(maxsplit=1)
                classes[int(cid)] = name.strip()

    panoptic = json.loads(pan_path.read_text(encoding="utf-8"))
    things = {c["id"]: c["name"] for c in panoptic["categories"] if c.get("isthing")}
    ann_map = {Path(a["file_name"]).stem: a for a in panoptic["annotations"]}
    ann = ann_map.get(image_name)

    if ann:
        for s in ann.get("segments_info", []):
            if s.get("category_id") in things and not s.get("iscrowd"):
                sx, sy, sw, sh = s["bbox"]
                cat_name = things[s["category_id"]]
                draw.rectangle([sx, sy, sx + sw, sy + sh], outline="magenta", width=2)
                draw.text((sx + 3, max(0, sy + sh - 14)), f"Pan: {cat_name} ({s['area']}px)", fill="magenta")

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
            draw.rectangle([x1, y1, x2, y2], outline="cyan", width=3)
            draw.text((x1 + 3, y1 + 3), f"Det: {cname}", fill="cyan")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def split_candidates_to_parts(candidates_path: Path, parts_dir: Path, num_parts: int = 6) -> None:
    doc = json.loads(candidates_path.read_text(encoding="utf-8"))
    cands = doc.get("candidates", [])
    parts_dir.mkdir(parents=True, exist_ok=True)
    buckets: list[list[dict]] = [[] for _ in range(num_parts)]
    for idx, c in enumerate(cands):
        buckets[idx % num_parts].append(c)

    for i, bucket in enumerate(buckets, start=1):
        pfile = parts_dir / f"review_part{i}.csv"
        if pfile.is_file():
            continue
        with pfile.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["image", "type", "verdict", "note"])
            writer.writeheader()
            for c in bucket:
                ctype = c["type"].split("/")[0].strip()
                writer.writerow(
                    {
                        "image": c["image"],
                        "type": ctype,
                        "verdict": "",
                        "note": "",
                    }
                )
    print(f"Đã chia {len(cands)} ứng viên vào {num_parts} phần tại {parts_dir}")


def merge_parts(parts_dir: Path, out_csv: Path) -> None:
    rows = []
    for pfile in sorted(parts_dir.glob("review_part*.csv")):
        with pfile.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                img = (r.get("image") or "").strip()
                tp = (r.get("type") or "").strip()
                verdict = (r.get("verdict") or "").strip()
                note = (r.get("note") or "").strip()
                if not img or not verdict:
                    continue
                if len(note) < 20:
                    raise ValueError(f"Ghi chú quá ngắn (< 20 ký tự) tại {pfile.name} ảnh {img}: '{note}'")
                rows.append({"image": img, "type": tp, "verdict": verdict, "note": note})

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["image", "type", "verdict", "note"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Đã gộp {len(rows)} dòng review hợp lệ vào {out_csv}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Vẽ box/segment lên ảnh ứng viên, chia 6 phần và gộp review_log.csv")
    parser.add_argument("--delivery", type=Path, default=Path("runs/r3007/delivery"))
    parser.add_argument("--candidates", type=Path, default=Path("runs/r3007/candidates.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("runs/r3007/visualized"))
    parser.add_argument("--parts-dir", type=Path, default=Path("runs/r3007/review_parts"))
    parser.add_argument("--merge-to", type=Path, help="Gộp các file review_part*.csv thành review_log.csv")
    parser.add_argument("--image", type=str, help="Vẽ riêng một ảnh")
    args = parser.parse_args()

    if args.merge_to:
        merge_parts(args.parts_dir, args.merge_to)
        return

    if args.image:
        visualize(args.delivery, args.image, args.out_dir / f"{args.image}_vis.jpg")
    elif args.candidates.is_file():
        doc = json.loads(args.candidates.read_text(encoding="utf-8"))
        images = sorted(list({c["image"] for c in doc.get("candidates", [])}))
        print(f"Đang vẽ {len(images)} ảnh ứng viên vào {args.out_dir}...")
        for img_name in images:
            visualize(args.delivery, img_name, args.out_dir / f"{img_name}_vis.jpg")
        split_candidates_to_parts(args.candidates, args.parts_dir, num_parts=6)
        print("Hoàn thành!")


if __name__ == "__main__":
    main()
