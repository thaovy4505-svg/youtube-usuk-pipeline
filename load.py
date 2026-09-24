import os
import pandas as pd
from datetime import datetime, timedelta 
from google.cloud import bigquery
from google.oauth2 import service_account

from config import GCP_PROJECT_ID, DATASET_ID, GOOGLE_APPLICATION_CREDENTIALS
from utils.logger import setup_logger

logger = setup_logger()

VIDEOS_SCHEMA = [
    bigquery.SchemaField("video_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("artist_name", "STRING"),
    bigquery.SchemaField("channel_id", "STRING"),
    bigquery.SchemaField("channel_title", "STRING"),
    bigquery.SchemaField("video_title", "STRING"),
    bigquery.SchemaField("description", "STRING"),
    bigquery.SchemaField("published_at", "TIMESTAMP"),
    bigquery.SchemaField("duration", "STRING"),
    bigquery.SchemaField("tags", "STRING"),
    bigquery.SchemaField("category_id", "STRING"),
    bigquery.SchemaField("view_count", "INTEGER"),
    bigquery.SchemaField("like_count", "INTEGER"),
    bigquery.SchemaField("comment_count", "INTEGER"),
    bigquery.SchemaField("extracted_at", "TIMESTAMP"),
    bigquery.SchemaField("ingestion_date", "DATE"),
    bigquery.SchemaField("engagement_rate", "FLOAT"),
    bigquery.SchemaField("duration_category", "STRING"),
]

COMMENTS_SCHEMA = [
    bigquery.SchemaField("comment_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("video_id", "STRING"),
    bigquery.SchemaField("artist_name", "STRING"),
    bigquery.SchemaField("channel_id", "STRING"),
    bigquery.SchemaField("parent_id", "STRING"),
    bigquery.SchemaField("author_name", "STRING"),
    bigquery.SchemaField("comment_text", "STRING"),
    bigquery.SchemaField("published_at", "TIMESTAMP"),
    bigquery.SchemaField("updated_at", "TIMESTAMP"),
    bigquery.SchemaField("like_count", "INTEGER"),
    bigquery.SchemaField("reply_count", "INTEGER"),
    bigquery.SchemaField("extracted_at", "TIMESTAMP"),
    bigquery.SchemaField("ingestion_date", "DATE"),
    bigquery.SchemaField("comment_length", "INTEGER"),
    bigquery.SchemaField("comment_category", "STRING"),
]


def get_bigquery_client():
    # Tạo kết nối tới BigQuery bằng service account key
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_APPLICATION_CREDENTIALS
    )
    return bigquery.Client(project=GCP_PROJECT_ID, credentials=credentials)


def create_table_if_not_exists(client, table_id, schema):
    try:
        client.get_table(table_id)
        logger.info(f"Bảng {table_id} đã tồn tại")
    except Exception:
        table = bigquery.Table(table_id, schema=schema)
        # Thêm expiration 30 ngày cho chế độ Sandbox
        table.expires = datetime.utcnow() + timedelta(days=30)
        client.create_table(table)
        logger.info(f"Đã tạo bảng {table_id}")


def load_to_bigquery(client, df, table_id, mode="WRITE_TRUNCATE"):
    # Đẩy DataFrame lên BigQuery, mode quyết định ghi đè hay thêm mới
    if df.empty:
        logger.warning(f"DataFrame rỗng, bỏ qua {table_id}")
        return False

    df_to_load = df.copy()
    for col in df_to_load.columns:
        if pd.api.types.is_datetime64_any_dtype(df_to_load[col]):
            df_to_load[col] = df_to_load[col].dt.strftime('%Y-%m-%d %H:%M:%S')

    job_config = bigquery.LoadJobConfig(write_disposition=mode)
    job = client.load_table_from_dataframe(df_to_load, table_id, job_config=job_config)
    job.result()

    table = client.get_table(table_id)
    logger.info(f"Đã load {len(df)} dòng lên {table_id}. Tổng: {table.num_rows} dòng")
    return True


def load_all_data(videos_df, comments_df):
    # Điều phối toàn bộ quá trình load lên BigQuery
    logger.info("Bắt đầu load dữ liệu lên BigQuery")

    client = get_bigquery_client()
    videos_table = f"{GCP_PROJECT_ID}.{DATASET_ID}.videos"
    comments_table = f"{GCP_PROJECT_ID}.{DATASET_ID}.comments"

    create_table_if_not_exists(client, videos_table, VIDEOS_SCHEMA)
    create_table_if_not_exists(client, comments_table, COMMENTS_SCHEMA)

    videos_ok = load_to_bigquery(client, videos_df, videos_table, mode="WRITE_TRUNCATE")
    comments_ok = load_to_bigquery(client, comments_df, comments_table, mode="WRITE_TRUNCATE")

    if videos_ok and comments_ok:
        logger.info("Load hoàn tất")
    else:
        logger.warning("Load chưa hoàn tất, kiểm tra lại")

    return {"videos": videos_ok, "comments": comments_ok}


if __name__ == "__main__":
    import json
    with open('data/raw_video_data.json', 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    from transform import clean_videos, clean_comments, transform_videos, transform_comments
    videos_df = transform_videos(clean_videos(raw_data['videos']))
    comments_df = transform_comments(clean_comments(raw_data['comments']))

    load_all_data(videos_df, comments_df)
