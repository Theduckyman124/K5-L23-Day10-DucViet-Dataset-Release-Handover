# Bảo mật khi làm việc

## 1. Ca USB: hết giờ, muốn chép lô về nhà làm tiếp
Tuyệt đối **không được chép lô dữ liệu (`runs/r3007/delivery/`) ra USB cá nhân**, gửi qua email cá nhân hay nhờ người ngoài mở giúp. Việc mang dữ liệu thô ra khỏi môi trường được cấp quyền sẽ làm mất khả năng kiểm soát truy cập, vi phạm cam kết bảo mật với khách hàng và có nguy cơ rò rỉ dữ liệu chưa phát hành. Giải pháp đúng là **lưu tiến độ công việc hiện tại trên máy công ty/máy trạm được cấp quyền**, ghi nhận trạng thái dở dang vào hệ thống quản lý job (`jobs.csv` / ticket nội bộ) và báo cho trưởng nhóm hoặc người phụ trách để bàn giao ca hoặc xin gia hạn vào ngày làm việc hôm sau.

## 2. Năm việc: được hay không
1. **Mở job được giao trên máy công ty**: **Được phép**, vì thao tác nằm trong đúng phạm vi công việc, đúng tài khoản được phân quyền và trên thiết bị đạt chuẩn bảo mật của dự án.
2. **Chụp màn hình gửi người quen**: **Không được phép**, vì làm lộ hình ảnh, nhãn và cấu trúc dự án ra bên ngoài cho người không có thẩm quyền.
3. **Chép lô ra USB**: **Không được phép**, vì thiết bị lưu trữ rời dễ thất lạc, nhiễm mã độc và làm rò rỉ toàn bộ lô dữ liệu.
4. **Dán nhãn thật hoặc dữ liệu thật của dự án lên chatbot công cộng**: **Không được phép**, vì dữ liệu tải lên các nền tảng AI công cộng có thể bị lưu trữ hoặc dùng để huấn luyện lại mô hình bên thứ ba (chỉ dữ liệu học tập công khai như COCO trong phòng lab mới được phép theo quy định môn học).
5. **Đưa tài khoản CVAT cho đồng nghiệp**: **Không được phép**, vì vi phạm nguyên tắc định danh cá nhân và làm sai lệch toàn bộ nhật ký truy vết trách nhiệm (`annotator` / `reviewer` trong `jobs.csv` và `truyvet.csv`).

## 3. Ca khuôn mặt: thấy mặt người rõ trong lô, guideline yêu cầu làm mờ
Khi phát hiện trong lô bàn giao có ảnh xuất hiện khuôn mặt người nhìn rõ (ví dụ các ảnh có nhãn `person` trong lô `r3007` như `000000004134`, `000000006763`, `000000007511`, `000000018150`) trong khi guideline yêu cầu phải làm mờ (anonymize/blur) thông tin định danh cá nhân (PII):
- **Trạng thái lô**: Chuyển ngay trạng thái lô sang **Hold** (tạm dừng phát hành, không đưa vào huấn luyện hay bàn giao tiếp).
- **Hành động**: Ghi nhận danh sách mã ảnh/cảnh bị lộ khuôn mặt và **báo ngay cho người phụ trách dữ liệu (Data Lead / Privacy Officer / PM)** để xử lý ở bước tiền xử lý nguồn.
- **Vì sao không tự ý làm mờ hay tự xoá ảnh**: Nếu kiểm duyệt viên tự ý chỉnh sửa/làm mờ file ảnh hoặc tự xoá ảnh khỏi lô thì sẽ làm thay đổi mã băm SHA-256 (`manifest.json`), phá vỡ tính toàn vẹn của bản gốc v1, làm lệch tọa độ nhãn và mất dấu vết kiểm toán (audit trail / lineage).
