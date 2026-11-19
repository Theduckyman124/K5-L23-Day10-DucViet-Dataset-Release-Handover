#!/usr/bin/env python3
"""Module của Thành viên 3: Đối chiếu chéo Detection (YOLO) ↔ Panoptic bằng pixel mask để sinh candidates.json."""
from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from pngutil import read_rgb  # noqa: E402


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def calc_iou(b1: list[float], b2: list[float]) -> float:
    ix1 = max(b1[0], b2[0])
    iy1 = max(b1[1], b2[1])
    ix2 = min(b1[2], b2[2])
    iy2 = min(b1[3], b2[3])
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    a1 = max(0.0, b1[2] - b1[0]) * max(0.0, b1[3] - b1[1])
    a2 = max(0.0, b2[2] - b2[0]) * max(0.0, b2[3] - b2[1])
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0


def count_seg_pixels_in_rect(
    pixels: bytes, width: int, height: int, seg_id: int, rect: list[float]
) -> int:
    """Đếm số pixel mang mã seg_id nằm trong hình chữ nhật rect = [x1, y1, x2, y2]."""
    x1 = max(0, min(width, int(math.floor(rect[0]))))
    y1 = max(0, min(height, int(math.floor(rect[1]))))
    x2 = max(0, min(width, int(math.ceil(rect[2]))))
    y2 = max(0, min(height, int(math.ceil(rect[3]))))
    if x2 <= x1 or y2 <= y1:
        return 0
    r = seg_id & 255
    g = (seg_id >> 8) & 255
    b = (seg_id >> 16) & 255
    count = 0
    stride = width * 3
    for y in range(y1, y2):
        row_start = y * stride + x1 * 3
        row_end = y * stride + x2 * 3
        for i in range(row_start, row_end, 3):
            if pixels[i] == r and pixels[i + 1] == g and pixels[i + 2] == b:
                count += 1
    return count


def find_candidates(root: Path, exclude_images: set[str] | None = None) -> list[dict]:
    """Đối chiếu detection (YOLO) và panoptic mask pixel để sinh danh sách ứng viên lỗi gán nhãn."""
    manifest = read_json(root / "manifest.json")["items"]
    panoptic = read_json(root / "panoptic.json")
    class_names: dict[int, str] = {}
    for line in (root / "classes.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            cid, name = line.split(maxsplit=1)
            class_names[int(cid)] = name.strip()

    things = {c["id"]: c["name"] for c in panoptic["categories"] if c.get("isthing")}
    dimensions = {im["id"]: (im["width"], im["height"]) for im in panoptic["images"]}
    annotations = {Path(a["file_name"]).stem: a for a in panoptic["annotations"]}
    excluded = exclude_images or set()

    candidates: list[dict] = []

    for image, item in manifest.items():
        if image in excluded:
            continue
        mask_path = root / item["mask"]
        label_path = root / item["label"]
        if not mask_path.is_file() or not label_path.is_file():
            continue

        ann = annotations[Path(item["mask"]).stem]
        width, height = dimensions[ann["image_id"]]

        # Đọc các box hợp lệ (loại bỏ box ngoài 0..79, box tràn biên hoặc box bị duplicate)
        boxes: list[dict] = []
        raw_boxes: list[tuple[int, float, float, float, float]] = []
        for line in label_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            parts = line.split()
            cls_f, x, y, w, h = map(float, parts[:5])
            if not cls_f.is_integer() or int(cls_f) not in class_names:
                continue
            if not all(map(math.isfinite, (x, y, w, h))) or w <= 0 or h <= 0:
                continue
            if x - w / 2 < -1e-6 or y - h / 2 < -1e-6 or x + w / 2 > 1 + 1e-6 or y + h / 2 > 1 + 1e-6:
                continue
            cls = int(cls_f)
            is_dup = False
            for ocls, ox, oy, ow, oh in raw_boxes:
                if (
                    cls == ocls
                    and abs(w - ow) * width < 0.01
                    and abs(h - oh) * height < 0.01
                    and abs(x - ox) * width <= 2.1
                    and abs(y - oy) * height <= 2.1
                ):
                    is_dup = True
                    break
            raw_boxes.append((cls, x, y, w, h))
            if is_dup:
                continue
            px1 = (x - w / 2) * width
            py1 = (y - h / 2) * height
            px2 = (x + w / 2) * width
            py2 = (y + h / 2) * height
            boxes.append(
                {
                    "cls": cls,
                    "name": class_names[cls],
                    "box": [px1, py1, px2, py2],
                    "bw": px2 - px1,
                    "bh": py2 - py1,
                    "area_px": max(1.0, (px2 - px1) * (py2 - py1)),
                    "area_norm": w * h,
                }
            )

        segs: list[dict] = []
        for s in ann["segments_info"]:
            if s["category_id"] in things and not s.get("iscrowd"):
                sx, sy, sw, sh = s["bbox"]
                segs.append(
                    {
                        "id": s["id"],
                        "category_id": s["category_id"],
                        "name": things[s["category_id"]],
                        "area": s.get("area", 0),
                        "bbox": [sx, sy, sw, sh],
                        "box": [sx, sy, sx + sw, sy + sh],
                        "sw": float(sw),
                        "sh": float(sh),
                    }
                )

        if not segs and not boxes:
            continue

        _, _, pixels = read_rgb(mask_path)

        # Tính số pixel thật của mỗi segment nằm trong bbox của chính nó
        for s in segs:
            s["true_pixels"] = count_seg_pixels_in_rect(
                pixels, width, height, s["id"], s["box"]
            )

        seg_by_cat: dict[str, list[dict]] = defaultdict(list)
        for s in segs:
            seg_by_cat[s["name"]].append(s)
        box_by_cls: dict[str, list[dict]] = defaultdict(list)
        for b in boxes:
            box_by_cls[b["name"]].append(b)

        # 1. Class swap / Category swap: box và segment trùng khớp vị trí + độ phủ pixel cao nhưng khác tên lớp
        swapped_seg_ids: set[int] = set()
        swapped_box_ids: set[int] = set()
        for b_idx, b in enumerate(boxes):
            if b["area_norm"] < 0.005:
                continue
            # Nếu box đã khớp tốt với một segment cùng lớp thì bỏ qua
            same_cls_ious = [calc_iou(b["box"], s["box"]) for s in seg_by_cat.get(b["name"], [])]
            if same_cls_ious and max(same_cls_ious) >= 0.5:
                continue

            best_seg = None
            best_iou = 0.0
            for s in segs:
                iou = calc_iou(b["box"], s["box"])
                if iou > best_iou:
                    best_iou = iou
                    best_seg = s

            if best_seg and best_iou >= 0.60 and b["name"] != best_seg["name"]:
                # Kiểm tra segment đó có box cùng lớp nào khớp hơn không
                seg_same_ious = [
                    calc_iou(best_seg["box"], ob["box"])
                    for ob in box_by_cls.get(best_seg["name"], [])
                ]
                if seg_same_ious and max(seg_same_ious) >= 0.5:
                    continue
                in_box_px = count_seg_pixels_in_rect(
                    pixels, width, height, best_seg["id"], b["box"]
                )
                cov = in_box_px / max(1, best_seg["true_pixels"])
                if cov >= 0.70:
                    swapped_seg_ids.add(best_seg["id"])
                    swapped_box_ids.add(b_idx)
                    candidates.append(
                        {
                            "image": image,
                            "type": "class_swap / category_swap",
                            "detail": (
                                f"Lệch lớp (IoU={best_iou:.2f}, phủ mask={cov:.0%}): "
                                f"Detection ghi '{b['name']}', Panoptic ghi '{best_seg['name']}'"
                            ),
                            "detection_class": b["name"],
                            "panoptic_class": best_seg["name"],
                        }
                    )

        # 2. Instance merge: 1 segment panoptic chứa pixel của >= 2 box detection CÙNG LỚP
        merged_seg_ids: set[int] = set()
        for cname, csegs in seg_by_cat.items():
            cboxes = [b for b_idx, b in enumerate(boxes) if b["name"] == cname and b_idx not in swapped_box_ids]
            if len(cboxes) <= len(csegs) or len(cboxes) < 2:
                continue
            for s in csegs:
                if s["true_pixels"] < 400:
                    continue
                covered_boxes = []
                total_in_boxes = 0
                for b in cboxes:
                    in_px = count_seg_pixels_in_rect(pixels, width, height, s["id"], b["box"])
                    box_fill = in_px / b["area_px"]
                    seg_share = in_px / max(1, s["true_pixels"])
                    if in_px >= 80 and (box_fill >= 0.25 or seg_share >= 0.18):
                        covered_boxes.append((b, in_px, seg_share))
                        total_in_boxes += in_px
                if len(covered_boxes) >= 2 and total_in_boxes / max(1, s["true_pixels"]) >= 0.65:
                    merged_seg_ids.add(s["id"])
                    candidates.append(
                        {
                            "image": image,
                            "type": "instance_merge",
                            "detail": (
                                f"Segment panoptic lớp '{cname}' (id={s['id']}) phủ pixel trên "
                                f"{len(covered_boxes)} box detection cùng lớp '{cname}'"
                            ),
                            "candidate_class": cname,
                        }
                    )

        # 3. Missing box: segment thing lớn nhưng không có box detection nào (kể cả box bị swap lớp) phủ pixel
        for cname, csegs in seg_by_cat.items():
            cboxes = box_by_cls.get(cname, [])
            if len(csegs) <= len(cboxes):
                continue
            for s in csegs:
                if s["id"] in swapped_seg_ids or s["id"] in merged_seg_ids:
                    continue
                if s["true_pixels"] < 1000:
                    continue
                # Kiểm tra độ phủ pixel với các box cùng lớp
                same_covs = [
                    count_seg_pixels_in_rect(pixels, width, height, s["id"], b["box"])
                    / max(1, s["true_pixels"])
                    for b in cboxes
                ]
                if same_covs and max(same_covs) >= 0.35:
                    continue
                # Kiểm tra xem có box khác lớp nào trùng khớp vị trí (tránh trùng với class_swap)
                any_ious = [calc_iou(s["box"], b["box"]) for b in boxes]
                if any_ious and max(any_ious) >= 0.60:
                    continue
                candidates.append(
                    {
                        "image": image,
                        "type": "missing_box",
                        "detail": (
                            f"Panoptic có vật '{cname}' (pixel={s['true_pixels']}) "
                            f"nhưng detection thiếu box"
                        ),
                        "candidate_class": cname,
                    }
                )

        # 4. Bbox drift: box cùng lớp với segment, giữ nguyên kích thước nhưng bị trượt lệch khỏi mask
        for cname, cboxes in box_by_cls.items():
            csegs = [s for s in seg_by_cat.get(cname, []) if s["id"] not in merged_seg_ids and s["true_pixels"] >= 400]
            if not csegs:
                continue
            for b in cboxes:
                if b["area_norm"] < 0.005:
                    continue
                best_s = max(csegs, key=lambda s: calc_iou(b["box"], s["box"]))
                iou = calc_iou(b["box"], best_s["box"])
                if not (0.25 <= iou < 0.85):
                    continue
                w_ratio = b["bw"] / max(1.0, best_s["sw"])
                h_ratio = b["bh"] / max(1.0, best_s["sh"])
                if not (0.85 <= w_ratio <= 1.15 and 0.85 <= h_ratio <= 1.15):
                    continue
                in_px = count_seg_pixels_in_rect(pixels, width, height, best_s["id"], b["box"])
                cov = in_px / max(1, best_s["true_pixels"])
                if 0.35 <= cov < 0.94:
                    candidates.append(
                        {
                            "image": image,
                            "type": "bbox_drift",
                            "detail": (
                                f"Box lớp '{cname}' bị lệch khỏi mask "
                                f"(IoU={iou:.2f}, pixel trong box={cov:.0%})"
                            ),
                            "candidate_class": cname,
                        }
                    )

    seen = set()
    unique_candidates = []
    for c in candidates:
        key = (c["image"], c["type"])
        if key not in seen:
            seen.add(key)
            unique_candidates.append(c)
    return unique_candidates
