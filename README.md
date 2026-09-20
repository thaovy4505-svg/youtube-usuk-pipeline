# 📈 BIG PROJECT 1 - ETL Pipeline lấy dữ liệu YouTube lên BigQuery

## 🛠️ Cài đặt

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 🔐 Cấu hình

Tạo file `.env` và thêm các thông tin sau:

```env
YOUTUBE_API_KEY=your_youtube_api_key_here
GCP_PROJECT_ID=your_project_id_here
DATASET_ID=youtube_data
GOOGLE_APPLICATION_CREDENTIALS=key.json
```

**Lưu ý:** File `key.json` là Service Account Key từ Google Cloud. Không commit file này lên GitHub.

## 🚀 Chạy

```bash
python3 main.py
```

**Chạy từng bước:**

```bash
# Chỉ Extract + Transform (bỏ qua Load)
python3 main.py --skip-load

# Chỉ Transform + Load (bỏ qua Extract)
python3 main.py --skip-extract

# Chỉ Load
python3 load.py
```

## 📁 Cấu trúc project

```
youtube_data_pipeline/
├── main.py                  # Entry point, điều phối pipeline
├── config.py                # Cấu hình: API key, project ID, danh sách nghệ sĩ
├── extract.py               # Gọi YouTube API lấy dữ liệu
├── transform.py             # Làm sạch và xử lý dữ liệu
├── load.py                  # Đẩy dữ liệu lên BigQuery
├── run_pipeline.sh          # Script chạy pipeline cho cron job
├── utils/
│   ├── __init__.py
│   └── logger.py            # Cấu hình logging
├── data/                    # Dữ liệu đầu ra
│   ├── raw_video_data.json  # Dữ liệu thô từ API
│   └── processed/           # Dữ liệu đã xử lý (CSV)
├── logs/
│   └── cron.log             # Log của cron job
├── requirements.txt         # Danh sách thư viện
└── README.md                # File này
```

## 📊 Kết quả

Dữ liệu được lưu vào 2 bảng trên BigQuery:

- **Bảng `videos`**: Thông tin chi tiết của từng video.
- **Bảng `comments`**: Comment của các video thuộc phạm vi đã chọn.

## 📋 Schema

### Bảng `videos`

| Nhóm trường | Trường | Mô tả |
|-------------|--------|-------|
| **Định danh** | `artist_name` | Tên nghệ sĩ |
| | `channel_id` | ID kênh YouTube |
| | `channel_title` | Tên kênh YouTube |
| | `video_id` | ID video |
| **Nội dung** | `video_title` | Tiêu đề video |
| | `description` | Mô tả video |
| | `published_at` | Ngày đăng video |
| | `duration` | Thời lượng video |
| | `tags` | Thẻ tag của video |
| | `category_id` | ID thể loại video |
| **Thống kê** | `view_count` | Lượt xem |
| | `like_count` | Lượt thích |
| | `comment_count` | Số comment |
| **Theo dõi pipeline** | `extracted_at` | Thời gian trích xuất |
| | `source` | Nguồn dữ liệu |
| | `ingestion_date` | Ngày nạp dữ liệu |

### Bảng `comments`

| Nhóm trường | Trường | Mô tả |
|-------------|--------|-------|
| **Định danh** | `artist_name` | Tên nghệ sĩ |
| | `channel_id` | ID kênh YouTube |
| | `video_id` | ID video |
| | `comment_id` | ID comment |
| | `parent_id` | ID comment cha (nếu là reply) |
| **Nội dung** | `author_name` | Tên người comment |
| | `comment_text` | Nội dung comment |
| | `published_at` | Ngày đăng comment |
| | `updated_at` | Ngày cập nhật comment |
| **Tương tác** | `like_count` | Lượt thích comment |
| | `reply_count` | Số phản hồi |
| **Theo dõi pipeline** | `extracted_at` | Thời gian trích xuất |
| | `ingestion_date` | Ngày nạp dữ liệu |

## ⚙️ Tham số

Có thể chỉnh sửa các tham số trong file `config.py`:

| Tham số | Mặc định | Ý nghĩa |
|---------|----------|---------|
| `ARTIST_YOUTUBE_IDS` | 100 nghệ sĩ | Danh sách nghệ sĩ và channel ID |
| `MAX_VIDEO_PER_CHANNEL` | `150` | Số video tối đa mỗi kênh |
| `MAX_COMMENTS_PER_VIDEO` | `50` | Số comment tối đa mỗi video |
| `TOP_VIDEOS_FOR_COMMENTS` | `30` | Số video lấy comment |

## ⏰ Tự động hóa

Pipeline có thể chạy tự động 2 lần/ngày bằng `crontab`.

### Bước 1: Cấp quyền thực thi cho script

File `run_pipeline.sh` đã có trong repo. Chỉ cần cấp quyền thực thi:

```bash
chmod +x run_pipeline.sh
```

### Bước 2: Cấu hình crontab

```bash
# Mở crontab
crontab -e

# Thêm 2 dòng sau (thay đường dẫn cho phù hợp với máy của bạn)
0 7 * * * $HOME/youtube_data_pipeline/run_pipeline.sh
0 23 * * * $HOME/youtube_data_pipeline/run_pipeline.sh
```

## 📝 Ghi chú

Dữ liệu được lấy từ [YouTube Data API v3](https://developers.google.com/youtube/v3), lưu trữ trên [Google BigQuery](https://cloud.google.com/bigquery).