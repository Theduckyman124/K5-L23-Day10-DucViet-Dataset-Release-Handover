# Công cụ xem ảnh và nhãn

## Chạy ứng dụng có backend

Từ thư mục gốc repo:

```bash
python3 tool/server.py
```

Mở **http://127.0.0.1:8765**. Lần đầu công cụ chuẩn bị ảnh và nhãn; các lần sau đọc cache. Mặc định dùng seed 3007. Chọn lô khác bằng `--delivery runs/r4007/delivery`, đổi cổng bằng `--port 8766`. Dùng `--rebuild` sau khi thay đổi dữ liệu nguồn hoặc cách vẽ lớp nhãn.

Ứng dụng đọc danh sách qua API, có chọn/tìm ảnh, phóng to/thu nhỏ và bốn chế độ xem. Nút **Thêm ảnh từ máy** tải ảnh lên backend và lưu lại qua lần tải trang hoặc khởi động lại. Ảnh mới chưa có nhãn nên chỉ xem được ảnh gốc. Ảnh trong delivery có box và viền được chuẩn bị từ nhãn có sẵn.

Điền người xem, loại lỗi, kết luận và bằng chứng (ít nhất 20 ký tự), rồi bấm **Lưu kết quả**. Chỉ ảnh thuộc delivery được ghi review. Lưu lại cùng ảnh và loại lỗi sẽ cập nhật kết quả cũ. Dùng **Tải review_log.csv** để lấy file dùng với `merge_review.py`. Các kết quả đã lưu được hiển thị khi chọn ảnh và loại lỗi tương ứng.

Dữ liệu ứng dụng nằm trong thư mục `review_app/` cạnh `delivery/`: catalog, ảnh hiển thị, uploads.json và reviews.json. Dữ liệu v1 không bị sửa. Backend chỉ nghe tại localhost. Dừng bằng Ctrl+C.

## Xuất trang xem tĩnh

Công cụ tạo trang HTML chạy cục bộ để đối chiếu ảnh, box detection và mask panoptic. Chỉ dùng dữ liệu trong `delivery/`; không gửi ảnh lên mạng. Cần Python 3.10+ và Pillow (chỉ công cụ xem ảnh dùng Pillow, validator vẫn dùng thư viện chuẩn).

Nếu chưa có Pillow: `python3 -m pip install Pillow`.

Chạy từ thư mục gốc repo, chọn một hoặc nhiều ảnh theo tên không có đuôi:

```bash
python3 tool/review_images.py runs/r3007/delivery --out runs/r3007/review_view --image 000000000139
```

Mở `runs/r3007/review_view/index.html` bằng trình duyệt. Có thể thêm `--image <tên>` nhiều lần. Bỏ `--image` để xuất toàn bộ ảnh; việc này tốn thời gian và dung lượng.

Khi đã có danh sách ứng viên, có thể lọc theo file đó:

```bash
python3 tool/review_images.py runs/r3007/delivery --out runs/r3007/review_view --candidates runs/r3007/candidates.json
```

JSON chấp nhận một danh sách hoặc object có khóa `candidates` (hay `errors`), mỗi phần tử là object có `image` hoặc `target`, và tùy chọn `type`. Công cụ **không tạo danh sách ứng viên** và không tự đưa ra kết luận. Ảnh thiếu hoặc không đọc được được ghi ra màn hình và bỏ qua.

Chọn ảnh từ danh sách bên phải, hộp chọn hoặc nút Trước/Sau. Ô tìm kiếm lọc theo tên ảnh hoặc loại ứng viên. Khi chạy không có `--candidates`, danh sách gồm toàn bộ ảnh được xuất, không phải danh sách lỗi đã xác định. Dùng các nút chế độ để xem ảnh gốc, bounding box, viền segmentation hoặc kết hợp. Box đỏ thể hiện detection; viền xanh thể hiện ranh giới pixel của segment thing (kể cả crowd) và các segment có category không hợp lệ. Mã P màu xanh trên ảnh tương ứng với danh sách segment bên cạnh; nhãn có thể chồng nhau. Dùng nút +/−, cuộn chuột trong khung, Vừa khung hoặc 100% để điều chỉnh kích thước. Thanh cuộn cho phép di chuyển khi ảnh lớn hơn khung. Nếu một dòng detection hoặc mask không đọc được, trang vẫn hiển thị ảnh và báo cảnh báo; không coi phần không hiển thị là nhãn rỗng.

Trang tĩnh chỉ dùng để xem ảnh đã xuất. Chức năng tải ảnh và lưu review cần mở ứng dụng qua backend như hướng dẫn phía trên.

Thành viên nhóm phải tự xem ảnh, ghi người xem, kết luận và bằng chứng vào `review_log.csv`; không xem ảnh hiển thị là kết quả xác nhận tự động.
