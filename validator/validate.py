#!/usr/bin/env python3
"""Validate the delivery's machine-checkable rules and cross-check candidates using only its files."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from pngutil import read_rgb


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(root: Path) -> list[dict[str, str]]:
    manifest = read_json(root / "manifest.json")["items"]
    metadata = read_json(root / "metadata.json")["items"]
    panoptic = read_json(root / "panoptic.json")
    with (root / "jobs.csv").open(encoding="utf-8", newline="") as stream:
        jobs = {row["job_id"]: row["guideline"] for row in csv.DictReader(stream)}
    classes = {int(line.split(maxsplit=1)[0]) for line in (root / "classes.txt").read_text(encoding="utf-8").splitlines() if line.strip()}
    categories = {c["id"]: c for c in panoptic["categories"]}
    dimensions = {im["id"]: (im["width"], im["height"]) for im in panoptic["images"]}
    annotations = {Path(a["file_name"]).stem: a for a in panoptic["annotations"]}
    errors: set[tuple[str, str]] = set()
    scenes: dict[str, set[str]] = defaultdict(set)
    for item in metadata:
        scenes[item["scene_id"]].add(item["split"])
        if item["guideline_version"] != jobs[item["job_id"]]:
            errors.add(("guideline_mismatch", item["image"]))
    for scene, splits in scenes.items():
        if len(splits) > 1:
            errors.add(("scene_leak", scene))

    for image, item in manifest.items():
        for kind in ("image", "label", "mask"):
            path = root / item[kind]
            if not path.is_file():
                if kind == "image":
                    errors.add(("missing_image", image))
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() != item[kind + "_sha256"]:
                errors.add(("wrong_hash", image))

        annotation = annotations[Path(item["mask"]).stem]
        width, height = dimensions[annotation["image_id"]]
        label = root / item["label"]
        boxes = []
        if label.is_file():
            for line in label.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                cls, x, y, w, h = map(float, line.split())
                if not cls.is_integer() or int(cls) not in classes:
                    errors.add(("invalid_class", image))
                if not all(map(math.isfinite, (x, y, w, h))) or w <= 0 or h <= 0 or x - w / 2 < -1e-6 or y - h / 2 < -1e-6 or x + w / 2 > 1 + 1e-6 or y + h / 2 > 1 + 1e-6:
                    errors.add(("bbox_out_of_bounds", image))
                for old_cls, ox, oy, ow, oh in boxes:
                    if cls == old_cls and abs(w - ow) * width < 0.01 and abs(h - oh) * height < 0.01 and abs(x - ox) * width <= 2.1 and abs(y - oy) * height <= 2.1:
                        errors.add(("duplicate_box", image))
                boxes.append((cls, x, y, w, h))

        segments = annotation["segments_info"]
        if any(s["category_id"] not in categories for s in segments):
            errors.add(("invalid_category_id", image))
        mask = root / item["mask"]
        if mask.is_file():
            _, _, pixels = read_rgb(mask)
            counts = Counter(pixels[i] + (pixels[i + 1] << 8) + (pixels[i + 2] << 16) for i in range(0, len(pixels), 3))
            for segment in segments:
                category = categories.get(segment["category_id"], {})
                if category.get("isthing") and segment["area"] > counts[segment["id"]]:
                    errors.add(("thing_overlap", image))
                    break
    return [{"type": kind, "target": target} for kind, target in sorted(errors)]


def find_candidates(root: Path) -> list[dict]:
    """Đối chiếu detection (YOLO) và panoptic để sinh danh sách ứng viên lỗi gán nhãn."""
    manifest = read_json(root / "manifest.json")["items"]
    panoptic = read_json(root / "panoptic.json")
    class_names = {}
    for line in (root / "classes.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            cid, name = line.split(maxsplit=1)
            class_names[int(cid)] = name.strip()

    things = {c["id"]: c["name"] for c in panoptic["categories"] if c.get("isthing")}
    dimensions = {im["id"]: (im["width"], im["height"]) for im in panoptic["images"]}
    annotations = {Path(a["file_name"]).stem: a for a in panoptic["annotations"]}

    def calc_iou(b1, b2):
        ix1 = max(b1[0], b2[0])
        iy1 = max(b1[1], b2[1])
        ix2 = min(b1[2], b2[2])
        iy2 = min(b1[3], b2[3])
        iw = max(0.0, ix2 - ix1)
        ih = max(0.0, iy2 - iy1)
        inter = iw * ih
        a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
        a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
        union = a1 + a2 - inter
        return inter / union if union > 0 else 0.0

    candidates = []
    for image, item in manifest.items():
        ann = annotations[Path(item["mask"]).stem]
        width, height = dimensions[ann["image_id"]]
        label = root / item["label"]
        boxes = []
        if label.is_file():
            for line in label.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                parts = line.split()
                cls = int(float(parts[0]))
                x, y, w, h = map(float, parts[1:5])
                px1 = (x - w / 2) * width
                py1 = (y - h / 2) * height
                px2 = (x + w / 2) * width
                py2 = (y + h / 2) * height
                cname = class_names.get(cls, str(cls))
                boxes.append({
                    "cls": cls,
                    "name": cname,
                    "box": [px1, py1, px2, py2],
                    "norm": (x, y, w, h),
                    "area_norm": w * h
                })

        segs = [s for s in ann["segments_info"] if s["category_id"] in things and not s.get("iscrowd")]
        for s in segs:
            sx, sy, sw, sh = s["bbox"]
            s["box"] = [sx, sy, sx + sw, sy + sh]
            s["name"] = things[s["category_id"]]

        seg_by_cat = defaultdict(list)
        for s in segs:
            seg_by_cat[s["name"]].append(s)
        box_by_cls = defaultdict(list)
        for b in boxes:
            box_by_cls[b["name"]].append(b)

        # 1. Missing box: panoptic segment có diện tích đáng kể nhưng detection thiếu box
        for cname, csegs in seg_by_cat.items():
            cboxes = box_by_cls.get(cname, [])
            if len(csegs) > len(cboxes):
                for s in csegs:
                    if s.get("area", 0) >= 1000:
                        ious = [calc_iou(s["box"], b["box"]) for b in cboxes]
                        if not ious or max(ious) < 0.5:
                            candidates.append({
                                "image": image,
                                "type": "missing_box",
                                "detail": f"Panoptic có vật '{cname}' (area={s['area']}) nhưng detection thiếu box",
                                "candidate_class": cname
                            })

        # 2. Instance merge: 1 segment panoptic bao trùm >= 2 box detection cùng lớp
        for s in segs:
            for cname, cboxes in box_by_cls.items():
                if len(cboxes) >= 2:
                    contained = []
                    for b in cboxes:
                        ix1 = max(s["box"][0], b["box"][0])
                        iy1 = max(s["box"][1], b["box"][1])
                        ix2 = min(s["box"][2], b["box"][2])
                        iy2 = min(s["box"][3], b["box"][3])
                        iw = max(0.0, ix2 - ix1)
                        ih = max(0.0, iy2 - iy1)
                        b_area = (b["box"][2] - b["box"][0]) * (b["box"][3] - b["box"][1])
                        if b_area > 0 and (iw * ih) / b_area > 0.5:
                            contained.append(b)
                    if len(contained) >= 2 and len(cboxes) > len(seg_by_cat.get(cname, [])):
                        candidates.append({
                            "image": image,
                            "type": "instance_merge",
                            "detail": f"Segment panoptic lớp '{cname}' bao trùm {len(contained)} box detection riêng biệt",
                            "candidate_class": cname
                        })

        # 3. Class swap / Category swap: cùng vị trí nhưng lệch tên lớp
        for b in boxes:
            best_seg = None
            best_iou = 0.0
            for s in segs:
                iou = calc_iou(b["box"], s["box"])
                if iou > best_iou:
                    best_iou = iou
                    best_seg = s
            if best_seg and best_iou >= 0.4:
                if b["name"] != best_seg["name"] and b["area_norm"] >= 0.005:
                    candidates.append({
                        "image": image,
                        "type": "class_swap / category_swap",
                        "detail": f"Lệch lớp (IoU={best_iou:.2f}): Detection ghi '{b['name']}', Panoptic ghi '{best_seg['name']}'",
                        "detection_class": b["name"],
                        "panoptic_class": best_seg["name"]
                    })

        # 4. Bbox drift: cùng lớp nhưng box detection bị trượt khỏi mask
        for b in boxes:
            if b["area_norm"] >= 0.005:
                matching_segs = [s for s in segs if s["name"] == b["name"]]
                if matching_segs:
                    best_s = max(matching_segs, key=lambda s: calc_iou(b["box"], s["box"]))
                    iou = calc_iou(b["box"], best_s["box"])
                    if 0.35 <= iou < 0.84:
                        candidates.append({
                            "image": image,
                            "type": "bbox_drift",
                            "detail": f"Box lớp '{b['name']}' bị lệch so với mask (IoU={iou:.2f})",
                            "candidate_class": b["name"]
                        })

    seen = set()
    unique_candidates = []
    for c in candidates:
        key = (c["image"], c["type"], c.get("detail"))
        if key not in seen:
            seen.add(key)
            unique_candidates.append(c)
    return unique_candidates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("delivery", type=Path, help="Đường dẫn tới thư mục delivery")
    parser.add_argument("--out", type=Path, required=True, help="File xuất lỗi JSON")
    parser.add_argument("--candidates", type=Path, help="Đường dẫn file xuất danh sách ứng viên (Pha 2)")
    args = parser.parse_args()

    errors = validate(args.delivery)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"errors": errors}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(errors)} rule findings written to {args.out}")

    if args.candidates:
        candidates = find_candidates(args.delivery)
        args.candidates.parent.mkdir(parents=True, exist_ok=True)
        args.candidates.write_text(json.dumps({"candidates": candidates, "total": len(candidates)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{len(candidates)} candidates written to {args.candidates} (across {len({c['image'] for c in candidates})} images)")


if __name__ == "__main__":
    main()
