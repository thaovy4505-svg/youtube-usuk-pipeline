import argparse
from datetime import datetime

from utils.logger import setup_logger
from extract import fetch_all_data
from transform import transform_all_data
from load import load_all_data

logger = setup_logger()


def parse_args():
    # Đọc tham số từ dòng lệnh khi chạy
    parser = argparse.ArgumentParser(description="YouTube ETL Pipeline")
    parser.add_argument(
        '--skip-extract',
        action='store_true',
        help='Bỏ qua bước extract, dùng dữ liệu raw đã có'
    )
    parser.add_argument(
        '--skip-load',
        action='store_true',
        help='Bỏ qua bước load lên BigQuery'
    )
    return parser.parse_args()


def run_pipeline(args):
    # Chạy toàn bộ pipeline ETL: Extract -> Transform -> Load
    start_time = datetime.now()
    logger.info("Bắt đầu pipeline ETL")

    try:
        # Extract
        if not args.skip_extract:
            logger.info("Bước 1: Extract dữ liệu từ YouTube API")
            fetch_all_data()
        else:
            logger.info("Bỏ qua bước Extract (dùng dữ liệu raw đã có)")

        # Transform
        logger.info("Bước 2: Transform dữ liệu")
        videos_df, comments_df = transform_all_data()

        # Load
        if not args.skip_load:
            logger.info("Bước 3: Load dữ liệu lên BigQuery")
            load_all_data(videos_df, comments_df)
        else:
            logger.info("Bỏ qua bước Load")

        # Tổng kết
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Pipeline hoàn tất trong {elapsed:.2f} giây")
        logger.info(f"Tổng: {len(videos_df)} video, {len(comments_df)} comment")

    except Exception as e:
        logger.error(f"Pipeline thất bại: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(args)