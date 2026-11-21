# Báo cáo nhóm DucViet

## 1. Số liệu luyện tập
- **F1 theo seed (rule / cross_check / overall)**:
  - **Seed `3007` (seed luyện tập chính của nhóm)**:
    - Khi mới chỉ kiểm tra lỗi luật (Pha 1, 11 lỗi luật): `1.0 / — / 0.7`.
    - Sau khi đối chiếu detection ↔ panoptic bằng pixel mask và review bằng mắt (Pha 2, 11 lỗi luật + 9 lỗi gán nhãn đã xác nhận = 20 lỗi): **`1.0 / 0.8 / 0.9`** (Truy vết `trace.json` đạt F1: `tier_a ≈ 1.0`, `tier_b ≈ 1.0`, `notify ≈ 1.0`).
  - **Lô sạch `runs/clean` (`--seed 5 --no-faults`, 50 ảnh pool `calib`)**: **`1.0 / 1.0 / 1.0`** (0 lỗi luật, 0 lỗi gán nhãn).
  - **Các seed kiểm thử bổ sung (`r3008`, `r4007`)**: F1 lỗi luật đều đạt `≈ 1.0`.
- **Số ứng viên trên lô sạch (`--no-faults`)**:
  - Cách ghép thô ban đầu (chỉ dùng IoU giữa 2 bounding box, ngưỡng lỏng): sinh khoảng 15–18 ứng viên nhiễu tự nhiên trên lô sạch `runs/clean` và **28 ứng viên (trên 18 ảnh)** trên seed `3007`.
  - Sau khi nâng cấp sang đối chiếu **pixel mask** (`validator/candidates.py`) và loại trừ các ảnh đã vi phạm lỗi luật: trên lô sạch `runs/clean` giảm xuống còn **0 ứng viên**; hàng đợi review trên seed luyện tập `3007` thu gọn còn **10 ứng viên trên 10 ảnh** (và trên đề ẩn là **13 ứng viên trên 13 ảnh**), vừa đủ nhỏ để 6 thành viên xem kỹ từng ảnh trong thời gian quy định.
- **Ngưỡng đã chọn và cách chọn (không dùng `_private`)**:
  - Nhóm hiệu chỉnh ngưỡng bằng cách chạy thử trên **lô sạch `runs/clean`** (50 ảnh không gài lỗi) để đo mức độ lệch tự nhiên giữa COCO detection và panoptic, kết hợp kiểm tra trực quan bằng công cụ `tool/`:
    1. **Loại trừ trước**: Bỏ qua các segment có `iscrowd=1`, các box vi phạm lỗi luật (`invalid_class`, `bbox_out_of_bounds`, `duplicate_box`) và các ảnh đã có lỗi luật (vì mỗi ảnh trong lô chỉ mang tối đa 1 lỗi).
    2. **`class_swap` / `category_swap`**: Chỉ bắt khi box có diện tích chuẩn hoá `>= 0.005`, không khớp với segment cùng lớp nào (`IoU < 0.50`), nhưng lại khớp vị trí rất chặt với một segment khác lớp (`IoU >= 0.60` và **tỷ lệ pixel của segment nằm trong box `>= 70%`**).
    3. **`instance_merge`**: Một segment panoptic (`true_pixels >= 400`) phủ lên `>= 2` box detection cùng lớp (mỗi box chứa `>= 80` pixel, chiếm `>= 25%` diện tích box hoặc `>= 18%` pixel của segment, và tổng pixel nằm trong các box chiếm `>= 65%` diện tích thật của segment).
    4. **`missing_box`**: Số segment lớp đó nhiều hơn số box detection cùng lớp, diện tích thật của segment `true_pixels >= 1000` pixel, nhưng độ phủ pixel với mọi box cùng lớp `< 35%` và không trùng vị trí (`IoU < 0.60`) với bất kỳ box khác lớp nào.
    5. **`bbox_drift`**: Box và segment cùng lớp có kích thước tương đương (`w_ratio, h_ratio` trong khoảng `[0.85, 1.15]`), nhưng vị trí bị trượt lệch khiến `0.25 <= IoU < 0.85` và tỷ lệ pixel mask nằm trong box rơi vào khoảng `[35%, 94%)`.

## 2. Vì sao báo hết ứng viên làm F1 giảm?
- Điểm đánh giá của lab là **F1**, tức trung bình điều hoà giữa **Precision** và **Recall**:
  $$\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}, \quad F1 = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$
- Trong bộ dữ liệu COCO gốc, nhãn detection và panoptic vốn có những **khác biệt tự nhiên** (vật ở xa hoặc ở mép ảnh chỉ được một bên gán nhãn, hai vật đứng trước-sau che khuất nhau làm bounding box chồng lấn, các thiết bị xếp chồng sát nhau...). Ngoài ra, với mỗi cặp bất đồng lớp giữa detection và panoptic, máy chỉ biết hai bên khác tên lớp chứ không thể tự biết bên nào đúng (`class_swap` hay `category_swap`).
- Nếu báo hết mọi ứng viên mà không mở ảnh xem bằng mắt:
  - Với bộ ghép thô ban đầu trên seed `3007` (11 lỗi luật + 28 ứng viên, đặc biệt nếu đẩy cả 2 chiều `class_swap` và `category_swap`), số lượng **báo thừa (FP)** tăng vọt trong khi số lỗi thật (TP) không đổi, kéo Precision giảm mạnh và làm tổng F1 tụt xuống mức ~0.6–0.7.
  - Ngay cả với bộ lọc pixel mask đã tinh chỉnh: trên seed `3007` có 10 ứng viên thì qua xem ảnh có **9 lỗi thật (`confirmed`)** và **1 ca lệch tự nhiên (`rejected` — ảnh `000000006763`)**; trên đề ẩn có 13 ứng viên thì có **11 lỗi thật (`confirmed`)** và **2 ca lệch tự nhiên (`rejected` — ảnh `img_0101`, `img_0230`)** cùng 5 ca phải nhìn ảnh thực tế mới phân định được là `class_swap` hay `category_swap`. Nếu không xem ảnh để loại các ca `rejected` và chọn đúng chiều lỗi lớp, mỗi ca đoán sai vừa tạo thêm 1 `FP` vừa mất 1 `TP` (thành `FN`), làm F1 giảm đáng kể. Hơn nữa, theo quy chế chấm điểm, mọi lỗi gán nhãn trong `errors.json` không có dòng `confirmed` kèm mô tả cụ thể trong `review_log.csv` đều bị loại bỏ.

## 3. Quyết định và lineage
- **Kết quả QC lô v1 (`lab250_c62afeb67fdb`)**:
  - Tổng số mục lỗi phát hiện trong `errors.json`: **20 / 250 ảnh = 8,0%** (gồm 11 lỗi luật và 9 lỗi gán nhãn đã xác nhận; mỗi ảnh/cảnh tính tối đa 1 lần).
  - **Kết luận cho v1**: **HOLD** (tạm dừng phát hành), vì tỷ lệ lỗi **8,0% vượt ngưỡng 2%** (quy tắc Day 7: trên 2% ảnh lỗi thì không được Release).
- **Xử lý trong lô bàn giao v2 (`lab250_c62afeb67fdb_v2`)**:
  - Giữ nguyên không chạm vào thư mục `delivery/` của v1.
  - Tách **9 ảnh lỗi ở nhãn detection** (`000000004134`, `000000005529`, `000000007511`, `000000007795`, `000000009483`, `000000013546`, `000000013923`, `000000022589`, `000000023272`) đưa vào `rework_queue.csv` và giao đúng cặp `annotator`/`reviewer` theo `jobs.csv`.
  - Mở kiểm tra 2 ảnh `wrong_hash` (`000000006723`, `000000020247`) thấy ảnh còn nguyên vẹn, mở bình thường nên giữ lại trong v2 và cập nhật mã băm SHA-256 đúng vào `manifest.csv`.
  - Đồng bộ lại split cho cảnh bị rò `scene_214` và chuẩn hoá phiên bản guideline theo `jobs.csv` cho `000000002157`, `000000003553` trong `truyvet.csv`.
  - Giữ lại **6 ảnh chỉ lỗi ở phía panoptic** (`000000009590`, `000000013291`, `000000013659`, `000000019742`, `000000022192`, `000000023781`) trong lô v2 (vì lô v2 là sản phẩm detection và nhãn detection của chúng vẫn đúng), đồng thời ghi chú rõ trong `README.txt` để báo riêng cho team panoptic.
  - Kết quả lô v2 còn **241 ảnh sạch với 1647 nhãn detection**, đủ điều kiện **Release** và được ghi nhận vào `lineage.jsonl` với `parent: lab250_c62afeb67fdb`.
- **Vì sao training run `R-021` phải được xem lại hoặc huấn luyện lại (`review_or_retrain`)?**:
  - Khi chạy `python scripts/lineage.py impact --release-id lab250_c62afeb67fdb`, hệ thống báo `R-021: affected=True action=review_or_retrain`.
  - Lý do: Mô hình trong run `R-021` đã được huấn luyện trực tiếp trên lô dữ liệu v1 (`lab250_c62afeb67fdb`) vốn chứa 8,0% lỗi (bao gồm các box sai lớp `class_swap`, lệch vị trí `bbox_drift`, thiếu box `missing_box`, class ngoài phạm vi `invalid_class`, tràn biên và đặc biệt là `scene_leak` ở `scene_214` làm rò rỉ ảnh cùng cảnh giữa tập `train` và `val`).
  - Việc sửa dữ liệu hay phát hành lô v2 trên ổ đĩa **không tự động sửa được trọng số (weights) của mô hình đã học sai** và cũng không làm chỉ số đánh giá (validation metrics) của `R-021` hết bị ảo do `scene_leak`. Vì vậy team AI bắt buộc phải đánh giá lại hoặc train lại mô hình trên lô v2 đã làm sạch.

## 4. Hash chứng minh gì, không chứng minh gì?
- **Mã băm SHA-256 chứng minh được**:
  - **Tính toàn vẹn dữ liệu ở mức byte (data integrity)**: File ảnh, file nhãn hay gói `.zip` kể từ lúc chốt manifest/đóng gói không bị sửa đổi ngẫu nhiên, không bị hỏng bit khi truyền tải hay bị ai đó âm thầm sửa tay mà không qua quy trình phát hành phiên bản mới.
  - **Tính tái lập và định danh phiên bản (reproducibility & provenance)**: Cùng một tập file đầu vào sẽ luôn cho ra đúng một mã SHA-256 duy nhất (như `release_id` của v1 hoặc file `.sha256` của gói v2), giúp kiểm chứng chính xác lô dữ liệu mà mô hình đã dùng để train.
- **Mã băm SHA-256 KHÔNG chứng minh được**:
  - **Chất lượng và độ đúng ngữ nghĩa của nhãn (semantic correctness)**: Hash khớp 100% không hề có nghĩa là nhãn gán đúng vật thể trong ảnh. Một file nhãn gán nhầm ô tô thành xe buýt (`class_swap`), vẽ lệch khung (`bbox_drift`), bỏ sót vật (`missing_box`) hay sai quy tắc guideline vẫn có mã SHA-256 hoàn toàn hợp lệ nếu manifest tính hash từ chính file lỗi đó. Do đó `check_handover.py` đạt PASS về hash/định dạng không thay thế được bước đối chiếu nguồn và kiểm tra ảnh bằng mắt người.

## 5. Truy vết
- **Tiêu chí phân tầng `tier_a`, `tier_b` và `notify`**:
  - Từ `incoming/ticket.md` và `guideline/changelog.md`, nhóm xác định lớp bị thay đổi quy tắc gán nhãn khi chuyển từ guideline cũ (`v1.2`) sang guideline mới (`v1.3`), cùng danh sách các cảnh (`scene_id`) mà team AI phản ánh trong ticket:
    - Với **seed `3007`**: lớp đổi quy tắc là **`bottle`**, các cảnh báo lỗi trong ticket là **`scene_197` và `scene_309`**.
    - Với **đề ẩn (`de_an`)**: lớp đổi quy tắc là **`bowl`**, các cảnh báo lỗi trong ticket là **`scene_208` và `scene_844`**.
  - **`tier_a` (khoanh vùng trực tiếp — ưu tiên mở kiểm tra ngay)**: Các ảnh nằm trong những `scene_id` mà team AI nêu trong ticket, thuộc các job làm theo **guideline cũ (`v1.2` trong `jobs.csv`)**, và trong file nhãn detection (`labels/<image>.txt`) có ít nhất một bounding box thuộc lớp bị đổi quy tắc (`bottle` đối với `r3007` → 2 ảnh: `000000002685`, `000000009590`; `bowl` đối với `de_an` → 3 ảnh: `img_0211`, `img_0223`, `img_0249`).
  - **`tier_b` (khoanh vùng mở rộng — rà soát phòng ngừa toàn lô)**: Các ảnh nằm ở các cảnh khác chưa bị team AI báo, nhưng có **cùng điều kiện rủi ro** (thuộc job làm theo guideline cũ `v1.2` trong `jobs.csv` và có ít nhất một box detection thuộc lớp bị đổi quy tắc) (`r3007` → 4 ảnh: `000000005193`, `000000006471`, `000000007574`, `000000008021`; `de_an` → 3 ảnh: `img_0075`, `img_0150`, `img_0174`).
  - **`notify`**: Tập hợp mã người gán (`annotator`) và người kiểm (`reviewer`) phụ trách các job chứa ảnh thuộc `tier_a` và `tier_b` (lấy từ `jobs.csv`).
- **Vì sao bắt buộc lấy phiên bản guideline theo `jobs.csv` chứ không lấy theo `metadata.json` của từng ảnh?**:
  - Phiên bản guideline áp dụng thực tế lúc giao việc được quy định ở cấp **job** trong `jobs.csv` (các job `J01`–`J04` làm theo `v1.2`, các job `J05`–`J10` làm theo `v1.3`).
  - Trường `guideline_version` ghi ở từng ảnh trong `metadata.json` có thể bị ghi sai do chính lỗi **`guideline_mismatch`** (ví dụ ảnh thuộc job `v1.2` nhưng metadata của ảnh lại bị gắn nhầm thành `v1.3`, hoặc ngược lại). Nếu truy vết dựa theo `metadata.json` của ảnh thì sẽ bỏ lọt những ảnh thực chất được gán theo quy tắc cũ `v1.2` nhưng bị ghi nhầm nhãn `v1.3`, hoặc báo nhầm ảnh thuộc job `v1.3`.

## 6. Bug hoặc điểm chưa rõ trong lab (nếu có)
- Không phát hiện bug trong bộ script chấm và kiểm tra của lab (`scripts/`). Một điểm kỹ thuật nhóm rút kinh nghiệm được trong quá trình làm là khi chạy trên Windows, cần luôn đọc file ở chế độ nhị phân (`rb`) khi băm SHA-256 và dùng `encoding="utf-8"` cho mọi thao tác đọc/ghi CSV, JSON để tránh lệch mã băm do chuyển đổi ký tự xuống dòng (`CRLF` vs `LF`) hoặc lỗi hiển thị tiếng Việt.
