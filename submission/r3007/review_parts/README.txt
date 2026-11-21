REVIEW PART 1 — SEED 3007
Trạng thái: đã chuẩn bị bằng chứng; CHƯA hoàn tất review của thành viên.
Phạm vi: 000000006763 và 000000019742. Bỏ qua Đề án 08 theo yêu cầu.

Mở trang xem ảnh từ thư mục gốc repo:
runs/r3007/review_part1_view/index.html
Trang có ảnh gốc, detection, panoptic và chế độ kết hợp; có thể phóng to.
Nếu cần tạo lại:
python3 tool/review_images.py runs/r3007/delivery --out runs/r3007/review_part1_view --image 000000006763 --image 000000019742

Các file:
- review_part1.csv: 3 dòng ứng viên cho 2 ảnh; verdict và reviewer còn trống.
- review_part1_evidence.json: nhãn, tọa độ pixel và SHA256 đọc từ delivery.
- Bản CSV làm việc tương ứng: runs/r3007/review_parts/review_part1.csv.

Cần người review thực hiện:
1. 000000006763 / instance_merge: detection có 3 person (D2,D3,D7), panoptic có 2 person không phải crowd. Xem vùng người phía trái, đối chiếu viền mask với từng người. Chênh lệch số lượng chưa đủ chứng minh instance_merge.
2. 000000019742 / class_swap và category_swap: detection ghi vase, panoptic ghi baseball bat ở cùng vùng. Xem hình dạng vật để quyết định bên nào sai. Nếu là vase, xác nhận category_swap và bác class_swap; nếu là baseball bat, làm ngược lại. Nếu không đủ rõ, tiếp tục để trống.
3. Điền verdict=confirmed hoặc rejected, reviewer=tên người thật sự xem và thay note bằng mô tả trực quan cụ thể (ít nhất 20 ký tự). Không coi ghi chú đối chiếu file là kết quả xem ảnh.
4. Đồng bộ bản CSV làm việc và bản trong submission sau khi chốt.
5. Gửi phần này để người tổng hợp ghép với các review_part khác vào review_log.csv. Chỉ sau khi ghép đủ các phần mới dùng merge_review.py để tạo errors.json cuối.

Các ô trống có chủ đích: merge_review.py bỏ qua chúng. Không dùng bản nháp này để tuyên bố đã hoàn thành review hay đã xác nhận lỗi.
Lô delivery và errors.json không bị thay đổi. Không đọc nhãn gốc hoặc _private, không dò đáp án bằng điểm F1.
