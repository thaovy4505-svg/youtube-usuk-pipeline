# transform.py
import os
import json
import logging
import csv 
from datetime import datetime

import pandas as pd
import numpy as np

from config import RAW_DATA_FILE, OUTPUT_FILE
from utils.logger import setup_logger

# CẤU HÌNH LOGGING
logger = setup_logger()


# ĐỌC DỮ LIỆU RAW TỪ JSON
def load_raw_data(filepath):
    try:
        logger.info(f"Đang đọc dữ liệu từ {filepath}...")
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Đã đọc {data.get('total_videos', 0)} video")
        return data
    except FileNotFoundError:
        logger.error(f"File {filepath} không tồn tại")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"File JSON bị lỗi: {e}")
        raise


# LÀM SẠCH DỮ LIỆU VIDEO
def clean_videos(videos_data):
    if not videos_data:
        logger.warning("Không có dữ liệu video để làm sạch")
        return pd.DataFrame()
    
    logger.info(f"Đang làm sạch {len(videos_data)} video...")
    df = pd.DataFrame(videos_data)
    
    numeric_cols = ['view_count', 'like_count', 'comment_count']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    if 'published_at' in df.columns:
        df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce')
    
    if 'extracted_at' in df.columns:
        df['extracted_at'] = pd.to_datetime(df['extracted_at'], errors='coerce')
    
    df['description'] = df['description'].fillna('')
    df['tags'] = df['tags'].fillna('')
    df['duration'] = df['duration'].fillna('')
    
    df = df.drop_duplicates(subset=['video_id'], keep='first')
    
    logger.info(f"Đã làm sạch xong. Còn {len(df)} video")
    return df

# LÀM SẠCH DỮ LIỆU COMMENT
def clean_comments(comments_data):
    if not comments_data:
        logger.warning("Không có dữ liệu comment để làm sạch")
        return pd.DataFrame()
    
    logger.info(f"Đang làm sạch {len(comments_data)} comment...")
    df = pd.DataFrame(comments_data)
    
    numeric_cols = ['like_count', 'reply_count']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    for col in ['published_at', 'updated_at', 'extracted_at']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    if 'comment_text' in df.columns:
        df['comment_text'] = df['comment_text'].astype(str).str.strip()
        df['comment_text'] = df['comment_text'].str.replace('\n', ' ', regex=False)
    
    df = df.drop_duplicates(subset=['comment_id'], keep='first')
    
    logger.info(f"Đã làm sạch xong. Còn {len(df)} comment")
    return df


# TRANSFORM VIDEO
import re

def classify_duration(duration_str):
    if not duration_str or not isinstance(duration_str, str):
        return 'Unknown'
    try:
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if not match:
            return 'Unknown'
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        total_minutes = hours * 60 + minutes + seconds / 60
        if total_minutes < 5:
            return 'Short'
        elif total_minutes < 20:
            return 'Medium'
        else:
            return 'Long'
    except Exception:
        return 'Unknown'


def transform_videos(df):
    if df.empty:
        return df
    
    logger.info("Đang thêm cột tính toán cho video...")
    df['ingestion_date'] = datetime.now().date()
    df['engagement_rate'] = np.where(
        df['view_count'] > 0,
        ((df['like_count'] + df['comment_count']) / df['view_count'] * 100).round(4),
        0
    )
    df['duration_category'] = df['duration'].apply(classify_duration)
    logger.info("Đã thêm cột tính toán cho video")
    return df


# TRANSFORM COMMENT
def transform_comments(df):
    if df.empty:
        return df
    
    logger.info("Đang thêm cột tính toán cho comment...")
    df['ingestion_date'] = datetime.now().date()
    df['comment_length'] = df['comment_text'].astype(str).str.len()
    df['comment_category'] = pd.cut(
        df['comment_length'],
        bins=[0, 50, 200, float('inf')],
        labels=['Short', 'Medium', 'Long']
    )
    logger.info("Đã thêm cột tính toán cho comment")
    return df


# LƯU DỮ LIỆU ĐÃ TRANSFORM
import csv

def save_transformed_data(videos_df, comments_df, output_dir='data/processed'):
    os.makedirs(output_dir, exist_ok=True)

    if not videos_df.empty:
        videos_path = os.path.join(output_dir, 'videos_transformed.csv')
        videos_df.to_csv(
            videos_path,
            index=False,
            encoding='utf-8-sig',
            quoting=csv.QUOTE_ALL,
            escapechar='\\'
        )
        logger.info(f"Đã lưu {len(videos_df)} video vào {videos_path}")

    if not comments_df.empty:
        comments_path = os.path.join(output_dir, 'comments_transformed.csv')
        comments_df.to_csv(
            comments_path,
            index=False,
            encoding='utf-8-sig',
            quoting=csv.QUOTE_ALL,
            escapechar='\\'
        )
        logger.info(f"Đã lưu {len(comments_df)} comment vào {comments_path}")


def transform_all_data(raw_data_file=RAW_DATA_FILE):
    logger.info("BẮT ĐẦU PIPELINE TRANSFORM")
    
    raw_data = load_raw_data(raw_data_file)
    videos_data = raw_data.get('videos', [])
    comments_data = raw_data.get('comments', [])
    
    videos_df = clean_videos(videos_data)
    comments_df = clean_comments(comments_data)
    
    videos_df = transform_videos(videos_df)
    comments_df = transform_comments(comments_df)
    
    save_transformed_data(videos_df, comments_df)
    
    logger.info(f"HOÀN TẤT TRANSFORM: {len(videos_df)} video, {len(comments_df)} comment")    
    return videos_df, comments_df


if __name__ == "__main__":
    videos_df, comments_df = transform_all_data()
    print(f"\n Videos: {len(videos_df)} dòng")
    print(f"Comments: {len(comments_df)} dòng")
    print("\n 5 dòng đầu của videos:")
    print(videos_df.head())
    print("\n 5 dòng đầu của comments:")
    print(comments_df.head())