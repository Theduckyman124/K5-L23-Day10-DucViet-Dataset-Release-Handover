Release: lab250_c62afeb67fdb_v2
Parent: lab250_c62afeb67fdb
Số ảnh: 241
Số nhãn: 1647
Guideline: v1.2 (J01-J04), v1.3 (J05-J10)
QC v1: 20/250 = 8,0%
Kết luận v1: Hold — tỷ lệ lỗi 8,0% vượt ngưỡng 2% nên tạm dừng phát hành để tách ảnh lỗi và sửa metadata
Kết luận v2: Release — đã tách 9 ảnh lỗi detection sang rework_queue.csv, sửa hash/guideline/split cho các ảnh còn lại
Ghi chú: Đã mở kiểm tra các ảnh wrong_hash (000000006723, 000000020247) thấy ảnh nguyên vẹn nên cập nhật SHA-256 mới trong manifest.csv; đồng bộ split theo cảnh cho scene_214 và chuẩn hoá guideline theo jobs.csv cho 000000002157, 000000003553; 9 ảnh lỗi nhãn detection đã bàn giao đúng annotator/reviewer trong rework_queue.csv; các ảnh chỉ lỗi ở panoptic (000000009590 (instance_merge), 000000013291 (instance_merge), 000000013659 (thing_overlap), 000000019742 (category_swap), 000000022192 (thing_overlap), 000000023781 (category_swap)) giữ nguyên trong v2 và báo riêng cho team panoptic xử lý.
