# extract.py
import os
import json
import time
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import (
    YOUTUBE_API_KEY,
    ARTIST_YOUTUBE_IDS,
    MAX_VIDEO_PER_CHANNEL,
    MAX_COMMENTS_PER_VIDEO,
    TOP_VIDEOS_FOR_COMMENTS,
    RAW_DATA_FILE
)
from utils.logger import setup_logger

logger = setup_logger()


def get_youtube_client():
    # Khởi tạo kết nối tới YouTube Data API v3
    try:
        logger.info("Đang khởi tạo kết nối YouTube API...")
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        logger.info("Khởi tạo kết nối thành công.")
        return youtube
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo kết nối: {e}")
        raise


def get_uploads_playlist_id(youtube, channel_id):
    # Lấy ID playlist chứa tất cả video đã upload của kênh
    try:
        response = youtube.channels().list(
            part='contentDetails',
            id=channel_id
        ).execute()

        items = response.get('items', [])
        if not items:
            logger.warning(f"Không tìm thấy kênh với ID: {channel_id}")
            return None

        playlist_id = items[0]['contentDetails']['relatedPlaylists']['uploads']
        return playlist_id

    except HttpError as e:
        logger.error(f"Lỗi HTTP khi lấy playlist cho {channel_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Lỗi khi lấy playlist cho {channel_id}: {e}")
        return None


def get_video_ids_from_playlist(youtube, playlist_id, max_results):
    # Lấy danh sách video ID từ playlist uploads
    video_ids = []
    next_page_token = None

    try:
        while len(video_ids) < max_results:
            response = youtube.playlistItems().list(
                part='contentDetails',
                playlistId=playlist_id,
                maxResults=min(50, max_results - len(video_ids)),
                pageToken=next_page_token
            ).execute()

            items = response.get('items', [])
            if not items:
                break

            for item in items:
                video_id = item['contentDetails']['videoId']
                video_ids.append(video_id)

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

        logger.info(f"Đã lấy {len(video_ids)} video ID từ playlist")
        return video_ids

    except HttpError as e:
        logger.error(f"Lỗi HTTP khi lấy video từ playlist: {e}")
        return video_ids
    except Exception as e:
        logger.error(f"Lỗi khi lấy video từ playlist: {e}")
        return video_ids


def get_video_details(youtube, video_ids, artist_name, channel_id):
    # Lấy thông tin chi tiết của video
    all_videos = []

    try:
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]

            response = youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(batch)
            ).execute()

            for item in response.get('items', []):
                snippet = item.get('snippet', {})
                statistics = item.get('statistics', {})
                content_details = item.get('contentDetails', {})

                video_data = {
                    'video_id': item['id'],
                    'artist_name': artist_name,
                    'channel_id': channel_id,
                    'channel_title': snippet.get('channelTitle', ''),
                    'video_title': snippet.get('title', ''),
                    'description': snippet.get('description', ''),
                    'published_at': snippet.get('publishedAt', ''),
                    'duration': content_details.get('duration', ''),
                    'tags': ','.join(snippet.get('tags', [])),
                    'category_id': snippet.get('categoryId', ''),
                    'view_count': int(statistics.get('viewCount', 0)),
                    'like_count': int(statistics.get('likeCount', 0)),
                    'comment_count': int(statistics.get('commentCount', 0)),
                    'extracted_at': datetime.now().isoformat()
                }
                all_videos.append(video_data)

        logger.info(f"Đã lấy thông tin chi tiết của {len(all_videos)} video cho {artist_name}")
        return all_videos

    except HttpError as e:
        logger.error(f"Lỗi HTTP khi lấy thông tin video: {e}")
        return all_videos
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin video: {e}")
        return all_videos


def get_video_comments(youtube, video_id, max_results):
    # Lấy comment của một video
    comments = []
    next_page_token = None

    try:
        while len(comments) < max_results:
            response = youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=min(100, max_results - len(comments)),
                textFormat='plainText',
                order='relevance',
                pageToken=next_page_token
            ).execute()

            items = response.get('items', [])
            if not items:
                break

            for item in items:
                snippet = item['snippet']
                top_comment = snippet['topLevelComment']
                comment_snippet = top_comment['snippet']

                comment_data = {
                    'comment_id': item['id'],
                    'video_id': video_id,
                    'parent_id': top_comment['id'],
                    'author_name': comment_snippet.get('authorDisplayName', ''),
                    'comment_text': comment_snippet.get('textDisplay', ''),
                    'published_at': comment_snippet.get('publishedAt', ''),
                    'updated_at': comment_snippet.get('updatedAt', ''),
                    'like_count': int(comment_snippet.get('likeCount', 0)),
                    'reply_count': int(snippet.get('totalReplyCount', 0)),
                    'extracted_at': datetime.now().isoformat()
                }
                comments.append(comment_data)

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

        return comments

    except HttpError as e:
        if e.resp.status == 403:
            logger.warning(f"Video {video_id} bị tắt comment, bỏ qua")
            return []
        else:
            logger.error(f"Lỗi HTTP khi lấy comment cho video {video_id}: {e}")
            return []
    except Exception as e:
        logger.error(f"Lỗi khi lấy comment cho video {video_id}: {e}")
        return []


def save_to_json(data, filename):
    # Lưu dữ liệu vào file JSON
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Đã lưu dữ liệu vào {filename}")

    except Exception as e:
        logger.error(f"Lỗi khi lưu file JSON: {e}")
        raise


def fetch_all_data():
    # Hàm điều phối chính: lấy toàn bộ dữ liệu cho tất cả nghệ sĩ
    logger.info("BẮT ĐẦU PIPELINE EXTRACT")

    youtube = get_youtube_client()

    all_videos = []
    all_comments = []

    total_artists = len(ARTIST_YOUTUBE_IDS)

    for idx, (artist_name, channel_id) in enumerate(ARTIST_YOUTUBE_IDS.items(), 1):
        try:
            logger.info(f"[{idx}/{total_artists}] Đang xử lý nghệ sĩ: {artist_name}")

            playlist_id = get_uploads_playlist_id(youtube, channel_id)
            if not playlist_id:
                logger.warning(f"Bỏ qua {artist_name} vì không lấy được playlist")
                continue

            video_ids = get_video_ids_from_playlist(
                youtube, playlist_id, MAX_VIDEO_PER_CHANNEL
            )
            if not video_ids:
                logger.warning(f"Bỏ qua {artist_name} vì không có video")
                continue

            videos = get_video_details(youtube, video_ids, artist_name, channel_id)
            if not videos:
                logger.warning(f"Bỏ qua {artist_name} vì không lấy được thông tin video")
                continue

            all_videos.extend(videos)

            videos_sorted = sorted(videos, key=lambda x: x.get('view_count', 0), reverse=True)
            top_videos = videos_sorted[:TOP_VIDEOS_FOR_COMMENTS]

            logger.info(f"Lấy comment cho top {len(top_videos)} video của {artist_name}")

            for video in top_videos:
                comments = get_video_comments(
                    youtube, video['video_id'], MAX_COMMENTS_PER_VIDEO
                )

                for comment in comments:
                    comment['artist_name'] = artist_name
                    comment['channel_id'] = channel_id

                all_comments.extend(comments)

            logger.info(f"Hoàn tất {artist_name}: {len(videos)} video, {len(all_comments)} comment")

            time.sleep(1)

        except HttpError as e:
            logger.error(f"Lỗi HTTP khi xử lý {artist_name}: {e}")
            continue
        except Exception as e:
            logger.error(f"Lỗi khi xử lý {artist_name}: {e}")
            continue

    logger.info("LƯU DỮ LIỆU VÀO JSON")

    data_to_save = {
        'extracted_at': datetime.now().isoformat(),
        'total_artists': total_artists,
        'total_videos': len(all_videos),
        'total_comments': len(all_comments),
        'videos': all_videos,
        'comments': all_comments
    }

    save_to_json(data_to_save, RAW_DATA_FILE)

    logger.info(f"HOÀN TẤT: {len(all_videos)} video, {len(all_comments)} comment")

    return all_videos, all_comments


if __name__ == "__main__":
    fetch_all_data()