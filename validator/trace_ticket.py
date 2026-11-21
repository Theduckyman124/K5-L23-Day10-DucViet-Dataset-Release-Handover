#!/usr/bin/env python3
"""Công cụ của Thành viên 6: Tự động truy vết ticket của team AI (Pha 5) để xuất trace.json."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re


def trace_delivery(delivery_dir: Path, out_path: Path) -> dict:
    ticket_text = (delivery_dir / "incoming" / "ticket.md").read_text(encoding="utf-8")
    changelog_text = (delivery_dir / "guideline" / "changelog.md").read_text(encoding="utf-8")

    # 1. Trích xuất các scene_id được nêu trong ticket.md
    reported_scenes = set(re.findall(r"scene_\d+", ticket_text))

    # 2. Trích xuất tên lớp bị đổi quy tắc trong changelog.md / ticket.md (nằm trong dấu backtick `...`)
    backtick_terms = re.findall(r"`([^`]+)`", changelog_text) + re.findall(r"`([^`]+)`", ticket_text)
    class_to_id: dict[str, int] = {}
    for line in (delivery_dir / "classes.txt").read_text(encoding="utf-8").splitlines():
        if line.strip():
            cid, cname = line.split(maxsplit=1)
            class_to_id[cname.strip()] = int(cid)

    target_class_name = None
    for term in backtick_terms:
        if term.strip() in class_to_id:
            target_class_name = term.strip()
            break
    if target_class_name is None:
        raise ValueError(f"Không tìm thấy tên lớp hợp lệ trong changelog/ticket: {backtick_terms}")
    target_cid = class_to_id[target_class_name]

    # 3. Xác định phiên bản guideline cũ từ jobs.csv (phiên bản nhỏ hơn, ví dụ v1.2)
    with (delivery_dir / "jobs.csv").open(encoding="utf-8", newline="") as f:
        jobs = {row["job_id"]: row for row in csv.DictReader(f)}
    versions = sorted({j["guideline"] for j in jobs.values()})
    old_guideline = versions[0]

    # 4. Duyệt metadata.json và labels/*.txt để tìm ảnh thuộc job có guideline cũ + có ít nhất 1 box lớp target_cid
    meta_items = json.loads((delivery_dir / "metadata.json").read_text(encoding="utf-8"))["items"]
    manifest_items = json.loads((delivery_dir / "manifest.json").read_text(encoding="utf-8"))["items"]

    tier_a: list[str] = []
    tier_b: list[str] = []
    notify_people: set[str] = set()

    for m in meta_items:
        img_name = m["image"]
        job = jobs[m["job_id"]]
        # Bắt buộc lấy phiên bản guideline theo job trong jobs.csv, KHÔNG lấy theo m["guideline_version"]
        if job["guideline"] != old_guideline:
            continue

        lbl_rel = manifest_items.get(img_name, {}).get("label", f"labels/{img_name}.txt")
        lbl_path = delivery_dir / lbl_rel
        if not lbl_path.is_file():
            continue

        has_target_box = False
        for ln in lbl_path.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            cid_f = float(ln.split()[0])
            if cid_f.is_integer() and int(cid_f) == target_cid:
                has_target_box = True
                break

        if not has_target_box:
            continue

        if m["scene_id"] in reported_scenes:
            tier_a.append(img_name)
        else:
            tier_b.append(img_name)
        notify_people.add(job["annotator"])
        notify_people.add(job["reviewer"])

    result = {
        "tier_a": sorted(tier_a),
        "tier_b": sorted(tier_b),
        "notify": sorted(notify_people),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Đã ghi {out_path}: lớp='{target_class_name}' (guideline cũ={old_guideline}, scenes={sorted(reported_scenes)}) -> "
        f"tier_a={len(result['tier_a'])}, tier_b={len(result['tier_b'])}, notify={result['notify']}"
    )
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Truy vết ticket của team AI xuất ra trace.json")
    ap.add_argument("delivery", type=Path, help="Đường dẫn thư mục delivery (ví dụ runs/r3007/delivery)")
    ap.add_argument("--out", type=Path, required=True, help="Đường dẫn file trace.json xuất ra")
    args = ap.parse_args()
    trace_delivery(args.delivery, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
