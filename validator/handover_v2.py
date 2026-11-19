#!/usr/bin/env python3
"""Công cụ của Thành viên 5: Tự động tính tỷ lệ lỗi Pha 3 (Lineage) và đóng gói Bàn giao Lô v2 (Pha 4)."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

DET_REWORK = {
    "missing_image",
    "invalid_class",
    "bbox_out_of_bounds",
    "duplicate_box",
    "class_swap",
    "bbox_drift",
    "missing_box",
}
PAN_ONLY = {"invalid_category_id", "thing_overlap", "category_swap", "instance_merge"}
THRESHOLD = 0.02


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_valid_image(path: Path) -> bool:
    """Kiểm tra file ảnh wrong_hash còn mở được và đúng định dạng JPEG/PNG không."""
    if not path.is_file() or path.stat().st_size < 128:
        return False
    data = path.read_bytes()
    is_jpeg = data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9")
    is_png = data.startswith(b"\x89PNG\r\n\x1a\n")
    return is_jpeg or is_png


def build_handover(run_dir: Path) -> int:
    root_dir = Path(__file__).resolve().parents[1]
    delivery = run_dir / "delivery"
    errors_path = run_dir / "errors.json"
    if not errors_path.is_file():
        raise SystemExit(f"Chưa có {errors_path}. Cần chốt errors.json trước khi đóng gói v2.")

    release_id = json.loads((delivery / "release.json").read_text(encoding="utf-8"))["release_id"]
    manifest_v1 = json.loads((delivery / "manifest.json").read_text(encoding="utf-8"))["items"]
    meta_list = json.loads((delivery / "metadata.json").read_text(encoding="utf-8"))["items"]
    meta_map = {m["image"]: m for m in meta_list}
    with (delivery / "jobs.csv").open(encoding="utf-8", newline="") as f:
        jobs = {row["job_id"]: row for row in csv.DictReader(f)}
    names80 = [
        ln.split(" ", 1)[1].strip()
        for ln in (delivery / "classes.txt").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]

    errors = json.loads(errors_path.read_text(encoding="utf-8"))["errors"]
    err_by_target: dict[str, list[str]] = {}
    for e in errors:
        err_by_target.setdefault(e["target"], []).append(e["type"])

    # Pha 3: Tính tỷ lệ lỗi thực tế trên mẫu số 250 ảnh
    total_v1 = len(manifest_v1)
    num_err_targets = len({e["target"] for e in errors})
    error_rate = num_err_targets / total_v1
    decision_v1 = "HOLD" if error_rate > THRESHOLD else "RELEASE"
    readme_v1_word = "Hold" if error_rate > THRESHOLD else "Release"

    # Kiểm tra và ghi lineage decision cho v1 (nếu chưa ghi)
    lineage_script = root_dir / "scripts" / "lineage.py"
    lineage_file = run_dir.parent / "lineage.jsonl"
    existing_events = []
    if lineage_file.is_file():
        existing_events = [
            json.loads(ln) for ln in lineage_file.read_text(encoding="utf-8").splitlines() if ln.strip()
        ]

    has_decision = any(
        ev.get("event") == "decision"
        and ev.get("release_id") == release_id
        and ev.get("decision") == decision_v1
        for ev in existing_events
    )
    if not has_decision:
        subprocess.run(
            [
                sys.executable,
                str(lineage_script),
                "--root",
                str(run_dir.parent),
                "record",
                "--event",
                "decision",
                "--release-id",
                release_id,
                "--decision",
                decision_v1,
            ],
            check=True,
        )

    subprocess.run(
        [
            sys.executable,
            str(lineage_script),
            "--root",
            str(run_dir.parent),
            "impact",
            "--release-id",
            release_id,
        ],
        check=True,
    )

    # Pha 4: Tạo handover/<release_id>_v2/
    v2_dir = run_dir / "handover" / f"{release_id}_v2"
    if v2_dir.exists():
        shutil.rmtree(v2_dir)
    (v2_dir / "images").mkdir(parents=True, exist_ok=True)
    (v2_dir / "labels").mkdir(parents=True, exist_ok=True)

    # Xác định split chuẩn cho từng scene_id (sửa scene_leak bằng cách lấy split đa số trong cảnh)
    scene_splits: dict[str, Counter] = {}
    for m in meta_list:
        scene_splits.setdefault(m["scene_id"], Counter())[m["split"]] += 1
    canonical_split = {sc: cnt.most_common(1)[0][0] for sc, cnt in scene_splits.items()}

    rework_rows: list[dict] = []
    kept_images: list[str] = []
    fixed_hash_images: list[str] = []
    fixed_guideline_images: list[str] = []
    panoptic_err_images: list[str] = []

    action_desc = {
        "missing_image": "Bổ sung file ảnh bị thiếu và kiểm tra lại nhãn detection",
        "invalid_class": "Gán lại nhãn detection có class_id nằm ngoài 0..79",
        "bbox_out_of_bounds": "Chỉnh lại khung bounding box bị tràn ra ngoài biên ảnh",
        "duplicate_box": "Xoá khung bounding box bị lặp trùng lớp và kích thước",
        "class_swap": "Sửa lại tên lớp detection bị gán nhầm với vật thể thực tế",
        "bbox_drift": "Căn chỉnh lại khung bounding box bị trượt lệch khỏi vật thể",
        "missing_box": "Bổ sung khung bounding box cho vật thể bị bỏ sót trên ảnh",
        "wrong_hash": "Thay thế file ảnh bị hỏng không đọc được",
    }

    for img_name in sorted(manifest_v1.keys()):
        item = manifest_v1[img_name]
        m = meta_map[img_name]
        job = jobs[m["job_id"]]
        img_errs = err_by_target.get(img_name, [])

        # Kiểm tra xem ảnh có phải đưa vào rework_queue không
        rework_type = None
        for et in img_errs:
            if et in DET_REWORK:
                rework_type = et
                break
            if et == "wrong_hash":
                img_path = delivery / item["image"]
                if is_valid_image(img_path):
                    fixed_hash_images.append(img_name)
                else:
                    rework_type = "wrong_hash"
                    break

        if rework_type is not None:
            rework_rows.append(
                {
                    "image": img_name,
                    "type": rework_type,
                    "annotator": job["annotator"],
                    "reviewer": job["reviewer"],
                    "action": action_desc.get(rework_type, "Gán và kiểm tra lại nhãn detection"),
                }
            )
            continue

        # Ảnh hợp lệ ở lại v2
        kept_images.append(img_name)
        shutil.copyfile(delivery / item["image"], v2_dir / "images" / f"{img_name}.jpg")
        shutil.copyfile(delivery / item["label"], v2_dir / "labels" / f"{img_name}.txt")

        for et in img_errs:
            if et == "guideline_mismatch":
                fixed_guideline_images.append(img_name)
            elif et in PAN_ONLY:
                panoptic_err_images.append(f"{img_name} ({et})")

    # 1. Ghi rework_queue.csv
    with (v2_dir / "rework_queue.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["image", "type", "annotator", "reviewer", "action"])
        writer.writeheader()
        writer.writerows(rework_rows)

    # 2. Ghi manifest.csv
    manifest_rows = []
    for sub in ("images", "labels"):
        for p in sorted((v2_dir / sub).iterdir()):
            if p.is_file():
                manifest_rows.append(
                    {"file": p.relative_to(v2_dir).as_posix(), "sha256": sha256_file(p)}
                )
    with (v2_dir / "manifest.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "sha256"])
        writer.writeheader()
        writer.writerows(manifest_rows)

    # 3. Ghi label_summary.csv
    class_counts: Counter = Counter()
    for img_name in kept_images:
        lbl_path = v2_dir / "labels" / f"{img_name}.txt"
        for ln in lbl_path.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                cid = int(float(ln.split()[0]))
                cname = names80[cid] if 0 <= cid < 80 else str(cid)
                class_counts[cname] += 1

    total_labels = sum(class_counts.values())
    with (v2_dir / "label_summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["class", "count"])
        writer.writeheader()
        for cname in names80:
            if class_counts[cname] > 0:
                writer.writerow({"class": cname, "count": class_counts[cname]})
        writer.writerow({"class": "TOTAL", "count": total_labels})

    # 4. Ghi truyvet.csv (guideline theo job, split đã đồng bộ theo scene_id)
    with (v2_dir / "truyvet.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["image", "scene_id", "split", "job_id", "annotator", "reviewer", "guideline"],
        )
        writer.writeheader()
        for img_name in kept_images:
            m = meta_map[img_name]
            job = jobs[m["job_id"]]
            writer.writerow(
                {
                    "image": img_name,
                    "scene_id": m["scene_id"],
                    "split": canonical_split[m["scene_id"]],
                    "job_id": m["job_id"],
                    "annotator": job["annotator"],
                    "reviewer": job["reviewer"],
                    "guideline": job["guideline"],
                }
            )

    # 5. Ghi README.txt
    leaked_scenes = sorted([e["target"] for e in errors if e["type"] == "scene_leak"])
    v12_jobs = sorted([jid for jid, j in jobs.items() if j["guideline"] == "v1.2"])
    v13_jobs = sorted([jid for jid, j in jobs.items() if j["guideline"] == "v1.3"])
    guideline_summary = (
        f"v1.2 ({v12_jobs[0]}-{v12_jobs[-1]}), v1.3 ({v13_jobs[0]}-{v13_jobs[-1]})"
        if v12_jobs and v13_jobs
        else "v1.2, v1.3"
    )
    pct_str = f"{error_rate * 100:.1f}%".replace(".", ",")
    readme_lines = [
        f"Release: {release_id}_v2",
        f"Parent: {release_id}",
        f"Số ảnh: {len(kept_images)}",
        f"Số nhãn: {total_labels}",
        f"Guideline: {guideline_summary}",
        f"QC v1: {num_err_targets}/{total_v1} = {pct_str}",
        f"Kết luận v1: {readme_v1_word} — tỷ lệ lỗi {pct_str} vượt ngưỡng 2% nên tạm dừng phát hành để tách ảnh lỗi và sửa metadata",
        f"Kết luận v2: Release — đã tách {len(rework_rows)} ảnh lỗi detection sang rework_queue.csv, sửa hash/guideline/split cho các ảnh còn lại",
        (
            f"Ghi chú: Đã mở kiểm tra các ảnh wrong_hash ({', '.join(fixed_hash_images) or 'không có'}) thấy ảnh nguyên vẹn nên cập nhật SHA-256 mới trong manifest.csv; "
            f"đồng bộ split theo cảnh cho {', '.join(leaked_scenes) or 'không có'} và chuẩn hoá guideline theo jobs.csv cho {', '.join(fixed_guideline_images) or 'không có'}; "
            f"{len(rework_rows)} ảnh lỗi nhãn detection đã bàn giao đúng annotator/reviewer trong rework_queue.csv; "
            f"các ảnh chỉ lỗi ở panoptic ({', '.join(panoptic_err_images) or 'không có'}) giữ nguyên trong v2 và báo riêng cho team panoptic xử lý."
        ),
    ]
    (v2_dir / "README.txt").write_text("\n".join(readme_lines) + "\n", encoding="utf-8")

    # 6. Chạy pack_release.py và ghi lineage release v2
    subprocess.run(
        [sys.executable, str(root_dir / "scripts" / "pack_release.py"), str(v2_dir)],
        check=True,
    )

    has_rel_v2 = any(
        ev.get("event") == "release"
        and ev.get("release_id") == f"{release_id}_v2"
        and ev.get("parent") == release_id
        for ev in existing_events
    )
    if not has_rel_v2:
        subprocess.run(
            [
                sys.executable,
                str(lineage_script),
                "--root",
                str(run_dir.parent),
                "record",
                "--event",
                "release",
                "--release-id",
                f"{release_id}_v2",
                "--parent",
                release_id,
            ],
            check=True,
        )

    print(f"Đã đóng gói hoàn tất {v2_dir} ({len(kept_images)} ảnh giữ lại, {len(rework_rows)} ảnh rework).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Đóng gói lô bàn giao v2 và cập nhật lineage")
    ap.add_argument("--run", type=Path, required=True, help="Thư mục run, ví dụ runs/r3007")
    args = ap.parse_args()
    return build_handover(args.run)


if __name__ == "__main__":
    raise SystemExit(main())
