# Dùng AI

| # | Ai dùng | Công cụ | Prompt (tóm tắt) | AI sai ở đâu | Nhóm kiểm lại thế nào |
|---|---|---|---|---|---|
| 1 | Thành viên nhóm (cần bổ sung tên) | Codex | Phân tích quy trình làm bài; hoàn thành bước 2: viết validator kiểm tra lỗi luật. | Chưa ghi nhận lỗi cụ thể; cần tiếp tục kiểm tra khi triển khai phần đối chiếu. | Chạy validator trên seed 3007, seed 4007 và lô sạch; đo F1 bằng công cụ của lab. |
| 2 | Nguyễn Công Bảo Long (TV4) | Codex | Tạo công cụ hỗ trợ xem ảnh, box detection và mask panoptic trong thư mục `tool/`. | Bản nháp chưa thể hiện trực quan đủ cho quyết định review; nhãn có thể che phần hiển thị. | Kiểm tra trang tĩnh và backend trên dữ liệu thật; xem trực tiếp ảnh và tự kết luận không để công cụ xác nhận thay con người. |
| 3 | Nguyễn Công Bảo Long (TV4) | Codex | Nâng cấp giao diện xem ảnh, phóng to/thu nhỏ, chuyển ảnh và hiển thị viền segmentation. | Cần kiểm tra tương tác trên trình duyệt và lớp viền trên các ảnh khác nhau. | Chạy test `test_review_tool.py`, kiểm tra edge, cảnh báo và bảo toàn delivery. |
| 4 | Nguyễn Công Bảo Long (TV4) | Codex | Hoàn thiện backend tải/hiển thị ảnh và lưu kết quả review. | Bản trước chủ yếu là trang tĩnh hoặc chưa lưu trạng thái review theo ảnh. | Chạy `test_review_server.py`; kiểm tra upload, review, xuất CSV và không ghi dữ liệu vào delivery. |
