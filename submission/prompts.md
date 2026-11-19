# Dùng AI

| # | Ai dùng | Công cụ | Prompt (tóm tắt) | AI sai ở đâu | Nhóm kiểm lại thế nào |
|---|---|---|---|---|---|
| 1 | Thành viên nhóm (cần bổ sung tên) | Codex | Phân tích quy trình làm bài; hoàn thành bước 2: viết validator kiểm tra lỗi luật. | Chưa ghi nhận lỗi cụ thể; cần tiếp tục kiểm tra khi triển khai phần đối chiếu. | Chạy validator trên seed 3007, seed 4007 và lô sạch; đo F1 bằng công cụ của lab. |
| 2 | Thành viên nhóm (cần bổ sung tên) | Codex | Tạo công cụ hỗ trợ xem ảnh, box detection và mask panoptic trong thư mục tool. | Chưa ghi nhận lỗi cụ thể; cần nhóm kiểm tra hình hiển thị khi review. | Chạy thử xuất trang review cho một ảnh của seed 3007; nhóm cần kiểm tra trực quan và tự kết luận. |
| 3 | Thành viên nhóm (cần bổ sung tên) | Codex | Nâng cấp UI xem ảnh, phóng to thu nhỏ, chuyển ảnh và hiển thị viền segmentation. | Cần nhóm kiểm tra trực quan và thao tác giao diện. | Xuất thử hai ảnh, kiểm tra lớp viền có pixel và kiểm tra cú pháp JavaScript; chưa kiểm thử trên trình duyệt. |
| 4 | Thành viên nhóm (cần bổ sung tên) | Codex | Hoàn thiện logic công cụ review ảnh. | Cần nhóm kiểm tra trực quan trên trình duyệt. | Kiểm thử dữ liệu mẫu có nhãn lỗi và ranh giới mask; kiểm tra không ghi vào delivery và chạy trên lô thật. |
| 5 | Thành viên nhóm (cần bổ sung tên) | Codex | Đưa danh sách ảnh cần review vào UI và cho phép tìm ảnh. | Cần nhóm kiểm tra thao tác trong trình duyệt. | Chạy kiểm thử công cụ và kiểm tra cú pháp JavaScript; cập nhật trang của lô 3007. |
| 6 | Thành viên nhóm (cần bổ sung tên) | Codex | Cho phép chọn ảnh từ máy trực tiếp trong giao diện review. | Cần nhóm kiểm tra thao tác chọn ảnh trong trình duyệt. | Chạy kiểm thử công cụ và kiểm tra cú pháp JavaScript; ảnh thêm trực tiếp chưa được gắn nhãn. |
| 7 | Thành viên nhóm (cần bổ sung tên) | Codex | Hoàn thiện backend và nối UI tải ảnh, lưu review, xuất CSV. | Bản trước chỉ là trang tĩnh, chưa lưu ảnh qua backend. | Kiểm thử HTTP upload, tải ảnh, lưu và cập nhật review, xuất CSV, từ chối file lỗi; nhóm tự xem và quyết định nhãn. |
