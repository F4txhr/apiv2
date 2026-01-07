import yt_dlp
from typing import Dict, Any, List

def get_media_info(url: str) -> Dict[str, Any]:
    """
    Extracts media information using yt-dlp.
    Supports YouTube, TikTok, Instagram, Twitter, Facebook, etc.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'simulate': True, # Do not download the video files
        'skip_download': True,
        'extract_flat': False, # Need full info for formats
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Format resolutions/formats
            formats = []
            if 'formats' in info:
                for f in info['formats']:
                    # Filter generic/useful formats
                    if f.get('url'):
                        fmt = {
                            "format_id": f.get('format_id'),
                            "ext": f.get('ext'),
                            "resolution": f.get('resolution') or f"{f.get('width')}x{f.get('height')}",
                            "filesize": f.get('filesize'),
                            "url": f.get('url'),
                            "note": f.get('format_note'),
                            "vcodec": f.get('vcodec'),
                            "acodec": f.get('acodec')
                        }
                        formats.append(fmt)
            
            # Extract Sound Info
            sound_info = {
                "track": info.get('track'),
                "artist": info.get('artist'),
                "album": info.get('album')
            }

            return {
                "status": "success",
                "platform": info.get('extractor_key'),
                "title": info.get('title'),
                "description": info.get('description'),
                "thumbnail": info.get('thumbnail'),
                "uploader": info.get('uploader'),
                "uploader_id": info.get('uploader_id'),
                "duration": info.get('duration'),
                "view_count": info.get('view_count'),
                "like_count": info.get('like_count'),
                "dislike_count": info.get('dislike_count'), # YT removed this public API mostly
                "comment_count": info.get('comment_count'),
                "repost_count": info.get('repost_count'), # shares
                "tags": info.get('tags'),
                "sound_info": sound_info,
                "formats": formats,
                # Direct media link (Best video usually)
                "media_url": info.get('url') # Sometimes null if formats are present
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
