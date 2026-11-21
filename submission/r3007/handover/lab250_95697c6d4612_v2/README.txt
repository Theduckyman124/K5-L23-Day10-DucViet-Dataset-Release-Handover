Release: lab250_95697c6d4612_v2
Parent: lab250_95697c6d4612
Số ảnh: 246
Số nhãn: 1675
Guideline: v1.2 (J01-J04), v1.3 (J05-J10)
QC v1: 11/250 = 4,4%
Kết luận v1: Hold — tỷ lệ lỗi 4,4% vượt ngưỡng 2% nên tạm dừng phát hành để tách ảnh lỗi và sửa metadata
Kết luận v2: Release — đã tách 4 ảnh lỗi detection sang rework_queue.csv, sửa hash/guideline/split cho các ảnh còn lại
Ghi chú: Đã mở kiểm tra các ảnh wrong_hash (000000006723, 000000020247) thấy ảnh nguyên vẹn nên cập nhật SHA-256 mới trong manifest.csv; đồng bộ split theo cảnh cho scene_214 và chuẩn hoá guideline theo jobs.csv cho 000000002157, 000000003553; 4 ảnh lỗi nhãn detection đã bàn giao đúng annotator/reviewer trong rework_queue.csv; các ảnh chỉ lỗi ở panoptic (000000013659 (thing_overlap), 000000022192 (thing_overlap)) giữ nguyên trong v2 và báo riêng cho team panoptic xử lý.
