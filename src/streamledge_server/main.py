import json
import logging
import os
import random
import re
import sys
import threading
import time
from functools import lru_cache
from html import unescape
from logging.handlers import RotatingFileHandler
from urllib.parse import quote, urlencode

from curl_cffi import requests
from flask import Flask, render_template, make_response, request

import streamledge.config_utils
from streamledge.config_utils import (
    AppConfig,
    get_window_position,
    initialize_config
)
from streamledge.main import (
    base_url_to_service,
    get_service_or_default_window_settings,
    is_port_in_use,
    open_browser
)

if streamledge.config_utils.WINDOWS_OS:
    import ctypes
    from ctypes import wintypes

SERVICE_NAMES = {
    'youtube': 'YouTube',
    'twitch': 'Twitch',
    'kick': 'Kick'
}

TWITCH_PUBLIC_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"  # Twitch web client ID

def update_config(config_path=streamledge.config_utils.CONFIG_PATH):
    global CONFIG, config
    CONFIG = initialize_config(config_path)
    config = AppConfig(CONFIG)

# Initial config load
update_config()

def configure_logging(app):
    # File handler for logs
    file_handler = RotatingFileHandler(
        filename=app.config['LOG_FILE'],
        maxBytes=1_000_000,
        backupCount=4,
        encoding='utf-8'
    )

    class ColorStrippingFormatter(logging.Formatter):
        def format(self, record):
            message = super().format(record)
            return self.strip_ansi_colors(message)

        def strip_ansi_colors(self, text):
            return re.sub(r'\033\[[0-9;]*m', '', text)

    file_formatter = ColorStrippingFormatter('%(asctime)s %(levelname)s: %(message)s')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)

    # Console handler for stdout (no level prefix)
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(message)s')  # Just the message
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    # Attach to app.logger
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    # Attach both handlers to werkzeug logger
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.INFO)
    werkzeug_logger.addHandler(file_handler)
    werkzeug_logger.addHandler(console_handler)

    # Separate logger for file-only logging
    file_only_logger = logging.getLogger('file_only')
    file_only_logger.setLevel(logging.INFO)
    file_only_logger.addHandler(file_handler)
    file_only_logger.propagate = False  # Prevent bubbling to root logger

def log_player_url(player_url):
    """Logs the URL to console (with colors) and to file (without colors)"""
    # Colorful console output
    print(f"SERVING URL:\033[0m \033[96m{player_url}\033[0m")

    # Log to file only (no console)
    logging.getLogger('file_only').info(f"SERVING URL: {player_url}")

# Flask app and logging (needs to be initialized after config)
app = Flask(__name__, template_folder='templates')
log_dir = os.path.join(streamledge.config_utils.CONFIG_DIR, 'logs')
os.makedirs(log_dir, exist_ok=True)
app.config['LOG_FILE'] = os.path.join(log_dir, 'streamledge_server.log')
configure_logging(app)
ACTIVE_PORT = int(CONFIG['Server']['port'])

YOUTUBE_BASE_PARAMS = urlencode({
  # 'rel': 0,  # 0 == show related from same channel as video | default of 1 == show related from all channels
    'enablejsapi': 1,  # <-- NEED this for java to work
    'origin': f'http://localhost:{ACTIVE_PORT}'
})

_shutdown_timer = None
_shutdown_lock = threading.Lock()

@app.before_request
def _handle_cors_preflight():
    if request.method == 'OPTIONS':
        resp = make_response('', 204)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        return resp

@app.after_request
def _add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return response

def shutdown_server(delay=0.2):
    global _shutdown_timer

    with _shutdown_lock:
        # Cancel the existing timer if it's still active
        if _shutdown_timer and _shutdown_timer.is_alive():
            _shutdown_timer.cancel()

        # Create and start a new timer
        _shutdown_timer = threading.Timer(delay, lambda: os._exit(0))
        _shutdown_timer.start()

def error_page(message, code=400):
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
    <body style="
        background: #0e0e10;
        color: #efeff1;
        font-family: Arial, sans-serif;
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
        margin: 0;
    ">
        <div style="
            background: #1f1f23;
            padding: 2.5rem;
            border-radius: 8px;
            max-width: 80%;
            font-size: 1.4rem;
            line-height: 1.6;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            border-left: 4px solid #9147ff;
        ">{message}</div>
    </body>
    </html>
    """, code

def fullscreen_video(hwnd, service):  # service var for possible future use
    if streamledge.config_utils.WINDOWS_OS:
        # Save current cursor position
        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        
        # Get window dimensions
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        
        # Bring window to foreground
        ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        
        # Calculate click position (center)
        x = rect.left + (rect.right - rect.left) // 2
        y = rect.top + (rect.bottom - rect.top) // 2

        # YouTube: Double-click to fullscreen
        for _ in range(2):
            ctypes.windll.user32.SetCursorPos(x, y)
            time.sleep(0.1)  # also initial wait
            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)  # Left down
            time.sleep(0.01)
            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)  # Left up
        
        # Wait before restoring cursor position to avoid annoying static info popup
        time.sleep(0.1)
        
        # Restore original cursor position
        ctypes.windll.user32.SetCursorPos(pt.x, pt.y)

def wait_for_window(title, timeout=10, service="youtube"):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            hwnd = ctypes.windll.user32.FindWindowW(None, title + '\u200B')
            if hwnd != 0:
                fullscreen_video(hwnd, service)
                # 'self_destruct' work around - self destruct here if fullscreen used
                if config.SERVER_SELF_DESTRUCT: shutdown_server()
                return True
            time.sleep(0.1)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(0.5)  # Longer sleep on error to prevent spamming
    if config.SERVER_SELF_DESTRUCT: shutdown_server()
    return False

def renderer_helper(service, title, player_url):
    log_player_url(player_url)

    browser_config = CONFIG['Browser']

    config_service = base_url_to_service(service)
    config_height, config_x_pos, config_y_pos = get_service_or_default_window_settings(config_service, config)

    def get_param(key, default):
        value = request.args.get(key, type=int)
        if value is not None:
            return value
        return default

    # Apply settings (Flask request args take priority)
    height = get_param('height', config_height)
    width = round(height * 16 / 9)  # Auto-calculate width
    height = height + int(browser_config.get('titlebar_height', '0'))
    
    # Check if x_pos or y_pos were provided in request args
    x_pos_provided = 'x_pos' in request.args
    y_pos_provided = 'y_pos' in request.args
    
    x_pos = get_param('x_pos', config_x_pos)
    y_pos = get_param('y_pos', config_y_pos)

    should_center_x_pos = bool(config.WINDOW_CENTER_X_POS) and config.get_service_setting(config_service, 'x_pos') is None
    should_center_y_pos = bool(config.WINDOW_CENTER_Y_POS) and config.get_service_setting(config_service, 'y_pos') is None

    if should_center_x_pos or should_center_y_pos:
        x_pos, y_pos = get_window_position(
            height=height,
            width=width,
            default_x_pos=x_pos,
            default_y_pos=y_pos,
            center_x=not x_pos_provided and should_center_x_pos,
            center_y=not y_pos_provided and should_center_y_pos
        )

    # Add service suffix to title if enabled
    if browser_config.get('title_suffix', 'false').lower() == 'true':
        title += f" - {SERVICE_NAMES.get(service.lower(), service)}"

    # Fullscreen video if enabled -- currently only works on Windows OS and only for YouTube
    fsbutton = True if request.args.get('fsbutton', str(config.YOUTUBE_FSBUTTON)).lower() in ('1', 'true') else False
    should_fullscreen = False
    if streamledge.config_utils.WINDOWS_OS and service.lower() == "youtube" and fsbutton:
        should_fullscreen = True if request.args.get('fullscreen', str(config.YOUTUBE_FULLSCREEN)).lower() in ('1', 'true') else False
        if should_fullscreen:
            fs_thread = threading.Thread(
                target=wait_for_window,
                args=(title,),  # Positional argument
                kwargs={'service': service},
                daemon=False  # let run independently
            )
            fs_thread.start()

    # Choose template
    html_file = "play_youtube.html" if service.lower() == "youtube" else "play_video.html"

    # Update window title and/or autoclose if required - currently only for YouTube  
    autoclose = True if request.args.get('autoclose', str(config.YOUTUBE_AUTOCLOSE)).lower() in ('1', 'true') else False

    # Shutdown server if enabled -- handled in streamledge.py
    if config.SERVER_SELF_DESTRUCT and not should_fullscreen: shutdown_server()

    return render_template(
        html_file,
        icon_file=f'icons/{service.lower()}.ico',
        player_title=title,
        player_url=player_url,
        height=height,
        width=width,
        x_pos=x_pos,
        y_pos=y_pos,
        update_title=config.YOUTUBE_UPDATE_TITLE,
        autoclose=autoclose,
        fullscreen=should_fullscreen
    )

def run_in_streamledge(base_url):
    """Handle Streamledge browser launch with all original parameters"""
    # Prepare arguments excluding runStreamledge itself
    args = {k: v for k, v in request.args.items() if k.lower() != 'runstreamledge'}
    query_string = '&'.join(f"{k}={v}" for k, v in request.args.items() 
                  if k.lower() != 'runstreamledge')
    query_url = f"?{query_string}" if query_string else ''
    open_browser(base_url, query_url, args, config, override_args=args)
    return '', 204

### * YOUTUBE SECTION * ###

def youtube_determine_id_type(media_info):
    media_info = media_info.strip()
    
    # 1. Multi-video (comma-separated)
    if ',' in media_info:
        video_ids = [vid.strip() for vid in media_info.split(',')]
        if all(len(vid) == 11 and re.match(r'^[\w-]{11}$', vid) for vid in video_ids):
            return ('multi', video_ids)
    
    # 2. Standard playlists (34 chars)
    if len(media_info) == 34 and re.match(r'^[\w-]{34}$', media_info) and \
       media_info.startswith(('PL','OL','RD','UL','UU','FL')):
        return ('playlist', media_info)

    # 3. Single video (11 chars)
    if len(media_info) == 11 and re.match(r'^[\w-]{11}$', media_info):
        return ('video', media_info)
        
    # 4. Radio playlists (RD prefix with valid lengths)
    if (media_info.startswith('RD') and 
        len(media_info) in {13, 34, 36} and  # RD+video(11), RD+playlist(34), (15) = "made for you list" cannot be embedded
        re.match(r'^RD[\w-]+$', media_info)):
        return ('radio', media_info)
    
    return None

def youtube_get_video_title(video_id, max_retries=3):
    """Get YouTube video title with retry logic: Try oEmbed API first, fallback to scraping"""
    # Try YouTube's public oEmbed API (no key needed) with retries
    for attempt in range(max_retries):
        try:
            oembed_url = f"https://www.youtube.com/oembed?url=https://youtube.com/watch?v={video_id}&format=json"
            response = requests.get(oembed_url, timeout=(3.05, 5.0))
            
            if response.status_code == 200:
                return response.json().get("title", "YouTube Video")
            elif response.status_code == 404:
                # Video doesn't exist or is private
                return None
                
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            if attempt == max_retries - 1:
                print(f"oEmbed failed after {max_retries} attempts, falling back to scraping: {e}")
            else:
                time.sleep(1 * (attempt + 1))  # Exponential backoff
                continue

    # Fallback to scraping with retries
    for attempt in range(max_retries):
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            response = requests.get(url, impersonate="chrome120", timeout=(3.05, 5.0))
            response.raise_for_status()
            
            # Method 1: Extract from JSON (more reliable)
            match = re.search(r'var ytInitialPlayerResponse = ({.*?});', response.text)
            if match:
                try:
                    data = json.loads(match.group(1))
                    title = data.get('videoDetails', {}).get('title')
                    if title:
                        return unescape(title)
                except json.JSONDecodeError:
                    pass  # Fall through to next method
                
            # Method 2: Alternative JSON extraction
            match = re.search(r'"title":"(.*?)"(?=,"lengthSeconds")', response.text)
            if match:
                raw_title = match.group(1)
                return unescape(raw_title.encode('utf-8').decode('unicode-escape'))
            
            # Method 3: HTML title fallback
            title_match = re.search(r'<title>(.*?) - YouTube</title>', response.text)
            if title_match:
                return unescape(title_match.group(1))
                
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                print(f"Scraping fallback failed after {max_retries} attempts: {e}")
            else:
                time.sleep(1 * (attempt + 1))  # Exponential backoff
                continue

    return None  # no video found

def youtube_get_playlist_title(playlist_id, max_retries=3):
    """Get YouTube playlist title with retry logic: Try oEmbed first, fallback to scraping"""
    # Try YouTube's public oEmbed API (no key needed) with retries
    for attempt in range(max_retries):
        try:
            oembed_url = f"https://www.youtube.com/oembed?url=https://youtube.com/playlist?list={playlist_id}&format=json"
            response = requests.get(oembed_url, timeout=(3.05, 5.0))
            
            if response.status_code == 200:
                title = response.json().get("title")
                if title and title != "YouTube":
                    return title.replace(" - YouTube", "")
            elif response.status_code == 404:
                return None  # Playlist doesn't exist or is private
                
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            if attempt == max_retries - 1:
                print(f"oEmbed failed after {max_retries} attempts, falling back to scraping: {e}")
            else:
                time.sleep(1 * (attempt + 1))  # Exponential backoff
                continue

    # Fallback to scraping with retries
    for attempt in range(max_retries):
        try:
            url = f"https://www.youtube.com/playlist?list={playlist_id}"
            response = requests.get(url, impersonate="chrome120", timeout=(3.05, 5.0))
            response.raise_for_status()
            
            # Method 1: Extract from primary JSON structure
            pattern = re.compile(r'ytInitialData\s*=\s*({.*?});', re.DOTALL)
            match = pattern.search(response.text)
            
            if match:
                try:
                    data = json.loads(match.group(1))
                    title = (
                        data.get('metadata', {})
                        .get('playlistMetadataRenderer', {})
                        .get('title')
                    )
                    if title:
                        return unescape(title)
                except json.JSONDecodeError:
                    pass  # Fall through to next method
                
            # Method 2: Try alternate JSON path
            alt_match = re.search(r'"playlist":\{"title":\{"simpleText":"(.*?)"}', response.text)
            if alt_match:
                return unescape(alt_match.group(1))
            
            # Method 3: HTML title tag fallback
            html_title = re.search(r'<title>(.*?)(?: - YouTube)?</title>', response.text)
            if html_title and html_title.group(1) not in ["Play All", "YouTube"]:
                return unescape(html_title.group(1))
                
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                print(f"Scraping fallback failed after {max_retries} attempts: {e}")
            else:
                time.sleep(1 * (attempt + 1))  # Exponential backoff
                continue

    return None  # Ultimate fallback (None indicates failure)

def youtube_search(query, max_retries=3):
    """Search YouTube with retry logic, returns (title, video_id) of first result or None"""
    for attempt in range(max_retries):
        try:
            # Create search URL
            search_query = quote(query)
            url = f"https://www.youtube.com/results?search_query={search_query}"
            response = requests.get(url, impersonate="chrome120", timeout=(3.05, 5.0))
            response.raise_for_status()
            
            # First try: Extract from JSON data
            pattern = re.compile(r'ytInitialData\s*=\s*({.*?});', re.DOTALL)
            matches = pattern.search(response.text)
            
            if matches:
                try:
                    data = json.loads(matches.group(1))
                    contents = (data.get('contents', {})
                               .get('twoColumnSearchResultsRenderer', {})
                               .get('primaryContents', {})
                               .get('sectionListRenderer', {})
                               .get('contents', [{}])[0]
                               .get('itemSectionRenderer', {})
                               .get('contents', []))
                    
                    for item in contents:
                        if 'videoRenderer' in item:
                            video_renderer = item['videoRenderer']
                            video_id = video_renderer.get('videoId')
                            title = (video_renderer.get('title', {})
                                    .get('runs', [{}])[0]
                                    .get('text'))
                            if video_id and title:
                                return (title, video_id)
                except (json.JSONDecodeError, AttributeError, KeyError) as e:
                    if attempt == max_retries - 1:
                        print(f"JSON parsing failed after {max_retries} attempts: {e}")
            
            # Fallback: Try HTML scraping if JSON fails
            video_matches = re.finditer(
                r'{"videoId":"([^"]+)","title":{"runs":\[{"text":"([^"]+)"',
                response.text
            )
            for match in video_matches:
                if match.group(1) and match.group(2):
                    return (match.group(2), match.group(1))
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                print(f"Search failed after {max_retries} attempts: {e}")
                return None
            time.sleep(1 * (attempt + 1))  # Exponential backoff
            continue
            
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Unexpected error after {max_retries} attempts: {e}")
                return None
            time.sleep(1 * (attempt + 1))
            continue
    
    return None  # All attempts failed

def youtube_search_playlist(query, max_retries=3, retry_delay=2):
    """Search YouTube for playlists with updated JSON parsing and retry logic"""
    for attempt in range(max_retries):
        try:
            # Create search URL
            search_url = f"https://www.youtube.com/results?search_query={quote(query)}&sp=EgIQAw%3D%3D"
            
            response = requests.get(search_url, impersonate="chrome120", timeout=(3.05, 5.0))
            response.raise_for_status()
            
            # Extract JSON data
            match = re.search(r'ytInitialData\s*=\s*({.*?});', response.text, re.DOTALL)
            if not match:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
                
            try:
                data = json.loads(match.group(1))
                # Parse data
                def find_playlists(obj):
                    if isinstance(obj, dict):
                        # Check for playlist metadata in the structure
                        if 'metadata' in obj and 'lockupMetadataViewModel' in obj['metadata']:
                            metadata = obj['metadata']['lockupMetadataViewModel']
                            title = metadata.get('title', {}).get('content', '')
                            
                            # Look for playlist ID in metadata rows
                            if 'metadata' in metadata and 'contentMetadataViewModel' in metadata['metadata']:
                                for row in metadata['metadata']['contentMetadataViewModel'].get('metadataRows', []):
                                    for part in row.get('metadataParts', []):
                                        if 'text' in part and 'commandRuns' in part['text']:
                                            for cmd in part['text']['commandRuns']:
                                                if 'onTap' in cmd and 'innertubeCommand' in cmd['onTap']:
                                                    command = cmd['onTap']['innertubeCommand']
                                                    if 'watchEndpoint' in command and 'playlistId' in command['watchEndpoint']:
                                                        playlist_id = command['watchEndpoint']['playlistId']
                                                        if playlist_id and title:
                                                            yield (title, playlist_id)
                        
                        # Recursively search deeper
                        for value in obj.values():
                            yield from find_playlists(value)
                            
                    elif isinstance(obj, list):
                        for item in obj:
                            yield from find_playlists(item)
                
                # Get the first valid playlist
                for playlist in find_playlists(data):
                    return playlist
                    
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
                
            except Exception as e:
                print(f"JSON PARSE ERROR (attempt {attempt + 1}/{max_retries}): {type(e).__name__}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
                
        except Exception as e:
            print(f"REQUEST ERROR (attempt {attempt + 1}/{max_retries}): {type(e).__name__}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return None
    
    return None  # Should never reach here

class YouTubePlaylistExtractor:
    """
    Robust YouTube playlist extractor using internal API endpoints
    """

    def __init__(self):
        # Configure session with browser-like headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'X-YouTube-Client-Name': '1',  # Required for API access
            'X-YouTube-Client-Version': '2.20240215.01.00',  # Current web client
        })

    def _extract_playlist_json(self, html):
        """
        Extract the ytInitialData JSON from page HTML
        Returns parsed dict or None if not found
        """
        for pattern in [
            r'ytInitialData\s*=\s*({.+?})\s*;',
            r'window\s*\[\s*["\']ytInitialData["\']\s*\]\s*=\s*({.+?})\s*;'
        ]:
            match = re.search(pattern, html)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        return None

    def _find_continuation_token(self, data):
        """
        Recursively search through JSON for continuation tokens
        Returns token string or None if not found
        """
        if isinstance(data, dict):
            # Check for direct continuation items
            if 'continuationItemRenderer' in data:
                try:
                    return data['continuationItemRenderer']['continuationEndpoint']['continuationCommand']['token']
                except KeyError:
                    pass
            
            # Check alternative token locations
            if 'continuationCommand' in data:
                try:
                    return data['continuationCommand']['token']
                except (KeyError, TypeError):
                    pass
            
            # Recursively check all dict values
            for value in data.values():
                result = self._find_continuation_token(value)
                if result:
                    return result
        
        elif isinstance(data, list):
            # Recursively check list items
            for item in data:
                result = self._find_continuation_token(item)
                if result:
                    return result
        
        return None

    def _fetch_continuation_batch(self, continuation_token, playlist_url):
        """
        Fetch additional videos using continuation token
        Returns (new_videos, next_continuation_token)
        """
        api_url = "https://www.youtube.com/youtubei/v1/browse"
        data = {
            "context": {
                "client": {
                    "hl": "en",
                    "gl": "US",
                    "clientName": "WEB",
                    "clientVersion": "2.20240215.01.00",
                    "originalUrl": playlist_url
                }
            },
            "continuation": continuation_token
        }

        response = self.session.post(
            api_url,
            params={"key": "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"},  # YouTube's web client key
            json=data,
            timeout=(3.05, 5.0)
        )
        response_data = response.json()

        # Extract new videos and next continuation
        new_videos = []
        next_continuation = None
        
        try:
            items = response_data['onResponseReceivedActions'][0]\
                   ['appendContinuationItemsAction']['continuationItems']
            
            for item in items:
                if 'playlistVideoRenderer' in item:
                    new_videos.append(item['playlistVideoRenderer']['videoId'])
                elif 'continuationItemRenderer' in item:
                    next_continuation = item['continuationItemRenderer']['continuationEndpoint']\
                                     ['continuationCommand']['token']
        except (KeyError, IndexError):
            pass

        return new_videos, next_continuation
    
    def extract_all_videos(self, playlist_id, max_retries=3):
        """
        Main extraction method with retry logic
        Returns list of all video IDs in playlist or None if failed
        """
        MAX_VIDEOS_TO_PARSE = 10000
        RETRY_DELAY = 1  # seconds
        
        # Initial page request with retries
        playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
        initial_data = None
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(playlist_url, timeout=(3.05, 5.0))
                response.raise_for_status()
                initial_data = self._extract_playlist_json(response.text) or {}
                break
            except (requests.exceptions.RequestException, ValueError) as e:
                if attempt == max_retries - 1:
                    print(f"Failed to fetch initial playlist after {max_retries} attempts: {e}")
                    return None
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
    
        # Extract first batch of videos
        videos = []
        try:
            contents = initial_data['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]\
                     ['tabRenderer']['content']['sectionListRenderer']['contents'][0]\
                     ['itemSectionRenderer']['contents'][0]['playlistVideoListRenderer']['contents']
            videos.extend(
                item['playlistVideoRenderer']['videoId']
                for item in contents
                if 'playlistVideoRenderer' in item
            )
        except (KeyError, TypeError) as e:
            print(f"Initial video extraction failed: {e}")
    
        # Handle pagination via continuation tokens with retries
        continuation = self._find_continuation_token(initial_data)
        while continuation and len(videos) < MAX_VIDEOS_TO_PARSE:
            for attempt in range(max_retries):
                try:
                    new_videos, continuation = self._fetch_continuation_batch(
                        continuation, 
                        playlist_url
                    )
                    videos.extend(new_videos)
                    break  # Success, exit retry loop
                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"Failed to fetch continuation batch after {max_retries} attempts: {e}")
                        return videos  # Return what we have so far
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue

        return videos
    
def youtube_shuffle_playlist(playlist_id):
    extractor = YouTubePlaylistExtractor()
    try:
        # Get all video IDs
        video_ids = extractor.extract_all_videos(playlist_id)
        if not video_ids:
            return f"https://www.{config.YOUTUBE_DOMAIN}/embed/videoseries?list={playlist_id}"
        
        # Shuffle and build URL
        random.shuffle(video_ids)
        return (
            f"https://www.{config.YOUTUBE_DOMAIN}/embed/{video_ids[0]}"
            f"?playlist={','.join(video_ids[:200])}"  # URL length limit
        )
    except Exception:
        return f"https://www.{config.YOUTUBE_DOMAIN}/embed/videoseries?list={playlist_id}"
    
def youtube_segment_playlist(playlist_id, start_index):
    extractor = YouTubePlaylistExtractor()
    try:
        # Get all video IDs
        video_ids = extractor.extract_all_videos(playlist_id)
        if not video_ids or start_index >= len(video_ids):
            return f"https://www.{config.YOUTUBE_DOMAIN}/embed/videoseries?list={playlist_id}"
        
        # Slice the list starting from the user-defined index
        segment = video_ids[start_index:start_index + 200]

        return (
            f"https://www.{config.YOUTUBE_DOMAIN}/embed/{segment[0]}"
            f"?playlist={','.join(segment)}"
        )
    except Exception:
        return f"https://www.{config.YOUTUBE_DOMAIN}/embed/videoseries?list={playlist_id}"

def youtube_get_boolean_options():
    """Extract boolean options from request with config defaults"""
    muted = config.get_service_setting('YouTube', 'muted')
    if muted is None: muted = config.MUTED
    return {
        'shuffle': request.args.get('shuffle', str(config.YOUTUBE_SHUFFLE)).lower() in ('1', 'true'),
        'autoplay': request.args.get('autoplay', str(config.YOUTUBE_AUTOPLAY)).lower() in ('1', 'true'),
        'mute': request.args.get('muted', muted),
        'loop': request.args.get('loop', str(config.YOUTUBE_LOOP)).lower() in ('1', 'true'),
        'cc': request.args.get('cc', str(config.YOUTUBE_CC)).lower() in ('1', 'true'),
        'video_controls': request.args.get('video_controls', str(config.YOUTUBE_CONTROLS)).lower() in ('1', 'true'),
        'keyboard': request.args.get('keyboard', str(config.YOUTUBE_KEYBOARD)).lower() in ('1', 'true'),
        'fsbutton': request.args.get('fsbutton', str(config.YOUTUBE_FSBUTTON)).lower() in ('1', 'true'),
        'annotations': request.args.get('annotations', str(config.YOUTUBE_ANNOTATIONS)).lower() in ('1', 'true'),
    }

def youtube_build_player_url(base_url, boolean_options, language=None):
    """Add common parameters to player URL"""
    params = [
        f"autoplay={1 if boolean_options['autoplay'] else 0}",
        f"mute={1 if boolean_options['mute'] else 0}",
        f"loop={1 if boolean_options['loop'] else 0}",
        f"cc_load_policy={1 if boolean_options['cc'] else 0}",
        f"controls={1 if boolean_options['video_controls'] else 0}",
        f"disablekb={0 if boolean_options['keyboard'] else 1}",
        f"fs={1 if boolean_options['fsbutton'] else 0}",
    ]
    
    if config.YOUTUBE_DOMAIN == "youtube.com":
        params.extend([f"iv_load_policy={1 if boolean_options['annotations'] else 3}"])

    if language:
        params.extend([f"hl={language}", f"cc_lang_pref={language}"])
    
    return f"{base_url}&{'&'.join(params)}"

@app.route('/youtube')
def youtube_player():
    """Handle YouTube URLs with all parameters in query string"""
    if request.args.get('runStreamledge', '').lower() in ('1', 'true'):
        return run_in_streamledge('youtube')

    media_id = request.args.get('id')
    if not media_id:
        return error_page("Error: Missing YouTube ID parameter", 400)

    update_config(request.args.get('config') or streamledge.config_utils.CONFIG_PATH)

    clean_id = media_id.split('?')[0].split('&')[0].strip()
    boolean_options = youtube_get_boolean_options()

    result = youtube_determine_id_type(clean_id)
    if result is None:
        return error_page("Invalid YouTube content.", 400)
        
    id_type, clean_id = result  # Handle custom playlists
    clean_id = ','.join(clean_id[:200]) if isinstance(clean_id, list) else clean_id

    # Build base player URL based on content type
    if id_type == "video":
        title = youtube_get_video_title(clean_id)
        if not title: return error_page("Video not found", 400)
        try:
            start_time = int(request.args.get('startTime', 0))
        except (ValueError, TypeError):
            start_time = 0
        if boolean_options['loop']:
            clean_id = f"{clean_id}?playlist={clean_id}&"
        if start_time > 0:
            url_for_base = f"{clean_id}?start={start_time}&"
        else:
            url_for_base = f"{clean_id}?"
        base_url = f"https://www.{config.YOUTUBE_DOMAIN}/embed/{url_for_base}{YOUTUBE_BASE_PARAMS}"
    elif id_type == "playlist":
        title = youtube_get_playlist_title(clean_id) or "YouTube Playlist"
        plstart = request.args.get('plstart', default=0, type=int)
        if boolean_options['shuffle']:
            base_url = youtube_shuffle_playlist(clean_id) + f"&{YOUTUBE_BASE_PARAMS}"
        elif plstart:
            base_url = youtube_segment_playlist(clean_id, plstart) + f"&{YOUTUBE_BASE_PARAMS}"
        else:
            base_url = f"https://www.{config.YOUTUBE_DOMAIN}/embed/videoseries?list={clean_id}&{YOUTUBE_BASE_PARAMS}"
    elif id_type == "radio":
        video_title = youtube_get_video_title(clean_id[2:])
        if not video_title: return error_page("Invalid YouTube content", 400)
        title = f"Mix - {video_title}" if video_title else "YouTube Mix"
        base_url = f"https://www.{config.YOUTUBE_DOMAIN}/embed/videoseries?list={clean_id}&{YOUTUBE_BASE_PARAMS}"
    elif id_type == "multi":
        title = "Custom Playlist"
        base_url = f"https://www.{config.YOUTUBE_DOMAIN}/embed/videoseries?playlist={clean_id}&{YOUTUBE_BASE_PARAMS}"
    else:
        return error_page("Invalid YouTube content", 400)

    language = request.args.get('language')
    if not language:
        language = str(config.YOUTUBE_LANGUAGE)
    language = language.lower()

    player_url = youtube_build_player_url(base_url, boolean_options, language)
    return renderer_helper('youtube', title, player_url)

@app.route('/youtube_search')
def youtube_search_player():
    query = request.args.get('q', '')
    if not query:
        return error_page("Error: Missing search query parameter (q)", 400)

    update_config(request.args.get('config') or streamledge.config_utils.CONFIG_PATH)

    boolean_options = youtube_get_boolean_options()
    search_type = request.args.get('searchType', 'video')

    # Build base player URL based on search type
    if search_type == "video":
        video_info = youtube_search(query)
        if not video_info:
            return error_page("Error: YouTube Search Failed", 400)
        title, video_id = video_info
        try:
            start_time = int(request.args.get('startTime', 0))
        except (ValueError, TypeError):
            start_time = 0  # fallback if conversion fails
        if boolean_options['loop']:
            video_id = f"{video_id}?playlist={video_id}&" # need to add as playlist for video to loop
        if start_time > 0:
            url_for_base = f"{video_id}?start={start_time}&"
        else:
            url_for_base = f"{video_id}?"
        base_url = f"https://www.{config.YOUTUBE_DOMAIN}/embed/{url_for_base}{YOUTUBE_BASE_PARAMS}"
    elif search_type == "playlist":
        playlist_info = youtube_search_playlist(query)
        if not playlist_info:
            return error_page("Error: YouTube Search Failed", 400)
        title, playlist_id = playlist_info
        plstart = request.args.get('plstart', default=0, type=int)
        if boolean_options['shuffle']:
            base_url = youtube_shuffle_playlist(playlist_id) + f"&{YOUTUBE_BASE_PARAMS}"
        elif plstart:
            base_url = youtube_segment_playlist(playlist_id, plstart) + f"&{YOUTUBE_BASE_PARAMS}"
        else:
            base_url = f"https://www.{config.YOUTUBE_DOMAIN}/embed/videoseries?list={playlist_id}&{YOUTUBE_BASE_PARAMS}"
    elif search_type == "mix":
        video_info = youtube_search(query)
        if not video_info:
            return error_page("Error: YouTube Search Failed", 400)
        title, video_id = video_info
        title = f"Mix - {title}"
        base_url = f"https://www.{config.YOUTUBE_DOMAIN}/embed/videoseries?list=RD{video_id}&{YOUTUBE_BASE_PARAMS}"
    else:
        return error_page("Invalid YouTube search type. Valid options are video, playlist, mix", 400)

    language = request.args.get('language')
    if not language:
        language = str(config.YOUTUBE_LANGUAGE)
    language = language.lower()

    try:
        start_time = int(request.args.get('startTime', 0))
    except (ValueError, TypeError):
        start_time = 0  # fallback if conversion fails

    player_url = youtube_build_player_url(base_url, boolean_options, language)
    return renderer_helper('youtube', title, player_url)

### * TWITCH SECTION * ###

@lru_cache(maxsize=None)
def twitch_get_user_info(username, max_retries=3):
    username = username.lower().strip()
    
    for attempt in range(max_retries):
        try:
            query = """query { user(login: "%s") { displayName id login } }""" % username
            response = requests.post(
                'https://gql.twitch.tv/gql',
                json={'query': query},
                headers={
                    'Client-ID': TWITCH_PUBLIC_CLIENT_ID,
                    'User-Agent': 'Mozilla/5.0'
                },
                timeout=(3.05, 5.0)
            )
            
            # Handle rate limits
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                time.sleep(retry_after)
                continue
                
            data = response.json()
            
            # User exists case
            if user := data.get('data', {}).get('user'):
                display_name = user['displayName']
                has_non_english = bool(re.search(r'[^\x00-\x7F]', display_name))
                
                return {
                    'display_name': display_name,
                    'user_id': user['id'],
                    'login_name': user['login'],
                    'has_non_english': has_non_english  # Flag indicating special handling needed
                }
            
            # User doesn't exist case
            if 'data' in data and data['data']['user'] is None:
                return {
                    'error': 'user_not_found',
                    'message': f'User \'{username}\' not found on Twitch'
                }
                
        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                return {
                    'error': 'timeout',
                    'message': 'Twitch API timed out repeatedly'
                }
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                return {
                    'error': 'connection_error',
                    'message': str(e)
                }
        except Exception as e:
            return {
                'error': 'unexpected_error',
                'message': str(e)
            }
        
        # Progressive backoff: 0.5s, 1s, 1.5s
        if attempt < max_retries - 1:
            time.sleep(0.5 * (attempt + 1))
    
    return {
        'error': 'unknown_error',
        'message': 'Failed to get user info after retries'
    }

def twitch_get_latest_vodid(user_id, vods_ago=1, max_retries=3):
    vods_ago = max(1, int(vods_ago))  # Ensure it's at least 1

    for attempt in range(max_retries):
        try:
            query = f"""
            query {{
                user(id: "{user_id}") {{
                    videos(first: {vods_ago}, type: ARCHIVE, sort: TIME) {{
                        edges {{
                            node {{
                                id
                            }}
                        }}
                    }}
                }}
            }}
            """

            response = requests.post(
                'https://gql.twitch.tv/gql',
                json={'query': query},
                headers={
                    'Client-ID': TWITCH_PUBLIC_CLIENT_ID,
                    'User-Agent': 'Mozilla/5.0'
                },
                timeout=(3.05, 5.0)
            )

            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            data = response.json()

            edges = data.get('data', {}).get('user', {}).get('videos', {}).get('edges', [])
            if len(edges) >= vods_ago:
                return edges[vods_ago - 1]['node']['id']
            else:
                print(f"Only {len(edges)} VOD(s) found for user {user_id}, can't get VOD #{vods_ago}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = min(1.5 ** attempt, 3)
                time.sleep(wait_time)
                continue
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            break

    print("Error: All VOD fetch attempts failed")
    return None

def twitch_get_live_stream_qualities(channel, max_retries=3):
    for attempt in range(max_retries):
        try:
            # 1. Prepare variables for live stream
            variables = {
                "playerType": "embed",
                "isLive": True,
                "login": channel,
                "isVod": False,
                "vodID": ""
            }

            # 2. Get access token (with retry)
            token_data = None
            for token_attempt in range(max_retries):
                try:
                    token_response = requests.post(
                        "https://gql.twitch.tv/gql",
                        json={
                            "operationName": "PlaybackAccessToken",
                            "variables": variables,
                            "extensions": {
                                "persistedQuery": {
                                    "version": 1,
                                    "sha256Hash": "0828119ded1c13477966434e15800ff57ddacf13ba1911c129dc2200705b0712"
                                }
                            }
                        },
                        headers={
                            "Client-ID": TWITCH_PUBLIC_CLIENT_ID,
                            "User-Agent": "Mozilla/5.0"
                        },
                        timeout=(3.05, 5.0)
                    )
                    
                    if token_response.status_code == 404:
                        return []  # Channel not found or not streaming
                        
                    token_response.raise_for_status()
                    token_data = token_response.json()
                    
                    if "errors" in token_data:
                        if token_attempt < max_retries - 1:
                            time.sleep(min(1.5 ** token_attempt, 3))
                            continue
                        return []
                        
                    if not token_data.get("data", {}).get("streamPlaybackAccessToken"):
                        if token_attempt < max_retries - 1:
                            time.sleep(min(1.5 ** token_attempt, 3))
                            continue
                        return []
                        
                    break
                except Exception as e:
                    if token_attempt == max_retries - 1:
                        raise
                    time.sleep(min(1.5 ** token_attempt, 3))

            # 3. Fetch manifest (with retry)
            for manifest_attempt in range(max_retries):
                try:
                    base_url = f"https://usher.ttvnw.net/api/channel/hls/{channel}.m3u8"
                    params = {
                        'allow_source': 'true',
                        'token': token_data['data']['streamPlaybackAccessToken']['value'],
                        'sig': token_data['data']['streamPlaybackAccessToken']['signature'],
                        'allow_audio_only': 'false'
                    }
                    
                    manifest_response = requests.get(
                        base_url,
                        params=params,
                        headers={"User-Agent": "Mozilla/5.0"},
                        timeout=(3.05, 15)
                    )
                    
                    if manifest_response.status_code == 404:
                        return []  # Stream not available
                        
                    manifest_response.raise_for_status()
                    break
                except Exception as e:
                    if manifest_attempt == max_retries - 1:
                        raise
                    time.sleep(min(1.5 ** manifest_attempt, 3))

            # 4. Parse qualities
            qualities = set()
            for line in manifest_response.text.split('\n'):
                if match := re.search(r'NAME="([^"]+)"', line):
                    qualities.add(match.group(1))
                    
            return sorted(qualities) if qualities else []
            
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries} failed for live channel {channel}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(min(1.5 ** attempt, 3))
                continue
    
    print(f"ERROR: All attempts failed for live channel {channel}")
    return []

def twitch_get_vod_stream_qualities(vod_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            # 1. Prepare variables for VOD
            variables = {
                "playerType": "embed",
                "isLive": False,
                "login": "",
                "isVod": True,
                "vodID": vod_id
            }

            # 2. Get access token (with retry)
            token_data = None
            for token_attempt in range(max_retries):
                try:
                    token_response = requests.post(
                        "https://gql.twitch.tv/gql",
                        json={
                            "operationName": "PlaybackAccessToken",
                            "variables": variables,
                            "extensions": {
                                "persistedQuery": {
                                    "version": 1,
                                    "sha256Hash": "0828119ded1c13477966434e15800ff57ddacf13ba1911c129dc2200705b0712"
                                }
                            }
                        },
                        headers={
                            "Client-ID": TWITCH_PUBLIC_CLIENT_ID,
                            "User-Agent": "Mozilla/5.0"
                        },
                        timeout=(3.05, 5.0)
                    )
                    
                    if token_response.status_code == 404:
                        return []  # VOD not found
                        
                    token_response.raise_for_status()
                    token_data = token_response.json()
                    
                    if "errors" in token_data:
                        if token_attempt < max_retries - 1:
                            time.sleep(min(1.5 ** token_attempt, 3))
                            continue
                        return []
                        
                    if not token_data.get("data", {}).get("videoPlaybackAccessToken"):
                        if token_attempt < max_retries - 1:
                            time.sleep(min(1.5 ** token_attempt, 3))
                            continue
                        return []
                        
                    break
                except Exception as e:
                    if token_attempt == max_retries - 1:
                        raise
                    time.sleep(min(1.5 ** token_attempt, 3))

            # 3. Fetch manifest (with retry)
            for manifest_attempt in range(max_retries):
                try:
                    base_url = f"https://usher.ttvnw.net/vod/{vod_id}"
                    params = {
                        'allow_source': 'true',
                        'token': token_data['data']['videoPlaybackAccessToken']['value'],
                        'sig': token_data['data']['videoPlaybackAccessToken']['signature'],
                        'allow_audio_only': 'false'
                    }
                    
                    manifest_response = requests.get(
                        base_url,
                        params=params,
                        headers={"User-Agent": "Mozilla/5.0"},
                        timeout=(3.05, 15)
                    )
                    
                    if manifest_response.status_code == 404:
                        return []  # VOD not available
                        
                    manifest_response.raise_for_status()
                    break
                except Exception as e:
                    if manifest_attempt == max_retries - 1:
                        raise
                    time.sleep(min(1.5 ** manifest_attempt, 3))

            # 4. Parse qualities
            qualities = set()
            for line in manifest_response.text.split('\n'):
                if match := re.search(r'NAME="([^"]+)"', line):
                    qualities.add(match.group(1))
                    
            return sorted(qualities) if qualities else []
            
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries} failed for VOD {vod_id}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(min(1.5 ** attempt, 3))
                continue
    
    print(f"ERROR: All attempts failed for VOD {vod_id}")
    return []

def render_twitch_chat(title, username):
    browser_config = CONFIG['Browser']
    twitch_config = CONFIG['Twitch']
    dark_mode = True if twitch_config.get('chat_dark_mode', 'true').strip().lower() == 'true' else False
    player_url = f"https://www.twitch.tv/embed/{username.lower()}/chat?parent=localhost"
    if dark_mode:
        player_url += "&darkpopout"

    log_player_url(player_url)

    def get_param(key, default):
        value = request.args.get(key, type=int)
        if value is not None:
            return value
        return default

    try:
        config_height = int(twitch_config['chat_height'])
    except (KeyError, ValueError):
        config_height = config.TWITCH_CHAT_HEIGHT

    try:
        config_width = int(twitch_config['chat_width'])
    except (KeyError, ValueError):
        config_width = config.TWITCH_CHAT_WIDTH

    try:
        config_x_pos = int(twitch_config['chat_x_pos'])
    except (KeyError, ValueError):
        config_x_pos = config.TWITCH_CHAT_X_POS

    try:
        config_y_pos = int(twitch_config['chat_y_pos'])
    except (KeyError, ValueError):
        config_y_pos = config.TWITCH_CHAT_Y_POS

    # Apply settings (Flask request args take priority)
    height = get_param('height', config_height)
    width = get_param('width', config_width)
    height = height + int(browser_config.get('titlebar_height', '0'))
    x_pos = get_param('x_pos', config_x_pos)
    y_pos = get_param('y_pos', config_y_pos)

    # Check if x_pos or y_pos were provided in request args
    x_pos_provided = 'x_pos' in request.args
    y_pos_provided = 'y_pos' in request.args

    should_center_x_pos = bool(config.TWITCH_CENTER_CHAT_X_POS) and config.get_service_setting('Twitch', 'chat_x_pos') is None
    should_center_y_pos = bool(config.TWITCH_CENTER_CHAT_Y_POS) and config.get_service_setting('Twitch', 'chat_y_pos') is None

    if should_center_x_pos or should_center_y_pos:
        x_pos, y_pos = get_window_position(
            height=height,
            width=width,
            default_x_pos=x_pos,
            default_y_pos=y_pos,
            center_x=not x_pos_provided and should_center_x_pos,
            center_y=not y_pos_provided and should_center_y_pos
        )

    title = f"{title}'s Chat"
    # Add service suffix to title if enabled
    if browser_config.get('title_suffix', 'false').lower() == 'true':
        title += f" - Twitch"

    # Shutdown server if enabled -- handled in streamledge.py
    if config.SERVER_SELF_DESTRUCT: shutdown_server()

    return render_template(
        'twitch_chat.html',
        icon_file=f'icons/twitch.ico',
        player_title=title,
        player_url=player_url,
        height=height,
        width=width,
        x_pos=x_pos,
        y_pos=y_pos,
    )

@lru_cache(maxsize=None)
def twitch_get_clip_info(clip_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            query = """query { clip(slug: "%s") { 
                title
                broadcaster { displayName }
                durationSeconds
                viewCount
                createdAt
                thumbnailURL(width: 480, height: 272)
            } }""" % clip_id
            
            response = requests.post(
                'https://gql.twitch.tv/gql',
                json={'query': query},
                headers={
                    'Client-ID': TWITCH_PUBLIC_CLIENT_ID,
                    'User-Agent': 'Mozilla/5.0'
                },
                timeout=(3.05, 5.0)
            )
            
            # Handle rate limits
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                time.sleep(retry_after)
                continue
                
            response.raise_for_status()
            data = response.json()
            
            if not (clip := data.get('data', {}).get('clip')):
                print(f"No clip data found for {clip_id}")
                return None
                
            return {
                'display_name': clip['broadcaster']['displayName'],
                'clip_title': unescape(clip['title']),
                'duration': clip['durationSeconds'],
                'views': clip['viewCount'],
                'created_at': clip['createdAt'],
                'thumbnail_url': clip['thumbnailURL']
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = min(1.5 ** attempt, 3)  # Grows 0s, 1.5s, 2.25s, capped at 3s
                time.sleep(wait_time)
                continue
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            break
            
    print(f"Error: All attempts failed for clip {clip_id}")
    return None

@lru_cache(maxsize=None)
def twitch_get_vod_info(vodid, max_retries=3):
    for attempt in range(max_retries):
        try:
            query = """query { video(id: "%s") { 
                title
                owner { 
                    displayName
                    login
                }
                lengthSeconds
                createdAt
                viewCount
            } }""" % vodid
            
            response = requests.post(
                'https://gql.twitch.tv/gql',
                json={'query': query},
                headers={
                    'Client-ID': TWITCH_PUBLIC_CLIENT_ID,
                    'User-Agent': 'Mozilla/5.0'
                },
                timeout=(3.05, 5.0)
            )
            
            # Handle rate limits gracefully
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                time.sleep(retry_after)
                continue
                
            response.raise_for_status()
            data = response.json()
            
            if not (video := data.get('data', {}).get('video')):
                print(f"No VOD data found for {vodid}")
                return None
                
            # Check for non-English characters
            title = unescape(video['title'])
            display_name = video['owner']['displayName']
            has_non_english = bool(re.search(r'[^\x00-\x7F]', display_name))
            
            return {
                'display_name': display_name,
                'login_name': video['owner']['login'],  # Added login name
                'vod_title': title,
                'duration': f"{video['lengthSeconds']}s",
                'created_at': video['createdAt'],
                'views': video.get('viewCount', 0),
                'has_non_english': has_non_english,  # Flag for owner
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = min(1.5 ** attempt, 3)  # Grows 0s, 1.5s, 2.25s, capped at 3s
                time.sleep(wait_time)
                continue
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            break
            
    print(f"Error: All attempts failed for VOD {vodid}")
    return None

def twitch_get_final_stream_quality(preferred_qualities, available_qualities):
    def clean_quality(q):
        """Helper: Clean quality string and check if it's source"""
        is_source = '(source)' in q.lower()
        q_clean = q.lower().replace(' ', '').replace('(source)', '')
        return q_clean, is_source

    def parse_quality(q):
        """Helper: Extract (resolution, fps) from quality string"""
        q_clean, _ = clean_quality(q)
        if 'p' in q_clean:
            parts = q_clean.split('p')
            res = int(parts[0]) if parts[0].isdigit() else 0
            fps = None if len(parts[1]) == 0 else (int(parts[1]) if parts[1].isdigit() else 0)
            return (res, fps, q)
        return (0, None, q)

    def get_return_quality(q, is_highest=False):
        """Return 'chunked' for source or highest resolution, otherwise cleaned quality"""
        _, is_source = clean_quality(q)
        return 'chunked' if is_source or is_highest else q

    # Handle both single quality string and comma-separated list
    if isinstance(preferred_qualities, str):
        preferred_qualities = [q.strip() for q in preferred_qualities.split(',')]
    
    # First try exact matches in order of preferred_qualities
    for preferred_quality in preferred_qualities:
        pref_norm, _ = clean_quality(preferred_quality)
        for q in available_qualities:
            q_norm, is_source = clean_quality(q)
            if q_norm == pref_norm:
                res, _, _ = parse_quality(q)
                max_res = max((r for r, _, _ in [parse_quality(q) for q in available_qualities]), default=0)
                return get_return_quality(q, res == max_res)

    # If no exact matches found, use the lowest preferred quality as the fallback target
    # Parse all preferred qualities to find the lowest resolution
    parsed_preferred = [parse_quality(q) for q in preferred_qualities]
    min_pref_res = min((res for res, _, _ in parsed_preferred if res > 0), default=0)
    
    if min_pref_res == 0:
        return None

    # Prepare all available qualities with parsed data
    processed_qualities = []
    for q in available_qualities:
        res, fps, original_q = parse_quality(q)
        processed_qualities.append((res, fps, original_q))

    max_res = max((res for res, _, _ in processed_qualities), default=0)

    # Step 1: Look for base resolution (no FPS) at the fallback target resolution
    base_res_matches = [q for (res, fps, q) in processed_qualities if res == min_pref_res and fps is None]
    if base_res_matches:
        selected = base_res_matches[0]
        return get_return_quality(selected, parse_quality(selected)[0] == max_res)

    # Step 2: Find all available resolutions BELOW the fallback target resolution
    lower_res_qualities = [(res, fps, q) for (res, fps, q) in processed_qualities if res < min_pref_res]
    if lower_res_qualities:
        resolution_groups = {}
        for res, fps, q in lower_res_qualities:
            if res not in resolution_groups:
                resolution_groups[res] = []
            resolution_groups[res].append((fps or 0, q))

        best_qualities = []
        for res in resolution_groups:
            resolution_groups[res].sort(reverse=True, key=lambda x: x[0])
            best_qualities.append((res, resolution_groups[res][0][0], resolution_groups[res][0][1]))

        best_qualities.sort(reverse=True, key=lambda x: x[0])
        selected = best_qualities[0][2]
        return get_return_quality(selected, parse_quality(selected)[0] == max_res)

    # Step 3: If no lower resolutions available, consider same resolution with FPS
    same_res_qualities = [q for (res, fps, q) in processed_qualities if res == min_pref_res]
    if same_res_qualities:
        same_res_qualities.sort(reverse=True, key=lambda q: parse_quality(q)[1] or 0)
        selected = same_res_qualities[0]
        return get_return_quality(selected, parse_quality(selected)[0] == max_res)

    # Step 4: Final fallback to lowest available non-source quality
    non_source_qualities = [q for (res, fps, q) in processed_qualities if not clean_quality(q)[1]]
    if non_source_qualities:
        non_source_qualities.sort(key=lambda x: parse_quality(x)[0])  # Sort by resolution ascending
        selected = non_source_qualities[0]
        return get_return_quality(selected, parse_quality(selected)[0] == max_res)

    # Step 5: Absolute fallback to lowest available (even if source)
    processed_qualities.sort(key=lambda x: x[0])  # Sort by resolution ascending
    selected = processed_qualities[0][2]
    return get_return_quality(selected, parse_quality(selected)[0] == max_res)

def twitch_add_framerate_to_final_quality(quality):
    """Add '30' framerate if quality has no framerate and resolution is numeric"""
    if 'p' in quality:
        p_index = quality.find('p')
        resolution = quality[:p_index]
        has_framerate = quality[-1].isdigit()
        if resolution.isdigit() and not has_framerate:
            return quality + '30'
    return quality

def twitch_convert_quality_formats(quality):
    # Split if comma-separated, process each item, and rejoin
    qualities = [q.strip() for q in quality.split(',')]
    converted = []
    for q in qualities:
        q = q.lower()
        if q == 'source':
            converted.append('chunked')
        elif q == 'auto':
            converted.append(q)
        elif re.fullmatch(r'\d+p$', q):
            converted.append(q)  # Or append +30 here if needed
        elif re.fullmatch(r'\d+p(30|60)$', q):
            converted.append(q)
        else:
            converted.append(q)  # Leave unchanged if no match
    return ','.join(converted)

def twitch_parse_query():
    """Parse query parameters with proper type handling"""
    try:
        volume =  max(0, min(100, int(request.args.get('volume', config.TWITCH_VOLUME)))) / 100
    except (ValueError, TypeError):
        volume = config.TWITCH_VOLUME

    quality = twitch_convert_quality_formats(request.args.get('quality', config.TWITCH_QUALITY))

    def convert_bool_param(param_value, config_default):
        """Convert input to Twitch-compatible 'true'/'false' string"""

        # Handle list case (legacy support)
        if isinstance(config_default, list):
            config_default = config_default[0].lower() == 'true'
        
        if param_value is None:
            return 'true' if config_default else 'false'
        
        # Handle string/boolean inputs
        if isinstance(param_value, (str, bool)):
            val = str(param_value).lower()
            return 'true' if val in ('1', 'true') else 'false'
        
        # Handle list inputs
        if isinstance(param_value, (list, tuple)):
            val = str(param_value[0]).lower()
            return 'true' if val in ('1', 'true') else 'false'
        
        return 'true' if param_value else 'false'

    muted = config.get_service_setting('Twitch', 'muted')
    if muted is None: muted = config.MUTED

    return {
        'type': request.args.get('contentType', 'live'),
        'channel': request.args.get('channel', ''),
        'vodid': request.args.get('vodid', ''),
        't': request.args.get('vodStart', ''),
        'quality': quality,
        'muted': convert_bool_param(request.args.get('muted'), muted),
        'volume': str(volume),
        'extensions': convert_bool_param(
            request.args.get('enableExtensions'),
            config.TWITCH_EXTENSIONS[0] if isinstance(config.TWITCH_EXTENSIONS, list) else config.TWITCH_EXTENSIONS
        )
    }

@app.route('/twitch')
def twitch_player():
    # Check for runStreamledge flag (case-insensitive)
    if request.args.get('runStreamledge', '').lower() in ('1', 'true'):
        return run_in_streamledge('twitch')

    update_config(request.args.get('config') or streamledge.config_utils.CONFIG_PATH)

    # Parse params from query
    params = twitch_parse_query()
    
    # Verify channel name is specified
    if params['type'] in {'live', 'vod', 'chat'}:
        if not params['channel']:
            return error_page("Error: Channel name is required", 400)
        user_info = twitch_get_user_info(params['channel'])
        if user_info.get('error'):  # Safely check if error exists using .get()
            return error_page(f"Error: {user_info.get('message', 'Unknown error')}", 400)
        
        # For title, get standardized display name - either just 'DisplayName' or 'DisplayName (login name)' if required
        if user_info.get('has_non_english'):
            title = f"{user_info.get('display_name', params['channel'])} ({user_info.get('login_name')})"
        else:
            title = user_info.get('display_name', params['channel'])

    if params['type'] == "vod":
        try:
            vods_ago = int(request.args.get('vodsAgo', 1))
        except (TypeError, ValueError):
            vods_ago = 1
        vodid = twitch_get_latest_vodid(user_info['user_id'], vods_ago)
        if not vodid:
            return error_page("Error: No VOD found for this channel", 400)
        title = f"[VOD] {title}"
    elif params['type'] == "vodid":
        vodid = params['vodid']
        vod_info = twitch_get_vod_info(vodid)
        if not vod_info:
            return error_page(f"Error: VOD ID '{vodid}' not found.", 400)
        if vod_info.get('has_non_english'):
            title = f"[VOD] {vod_info.get('display_name', params['channel'])} ({vod_info.get('login_name')})"
        else:
            title = f"[VOD] {vod_info.get('display_name', params['channel'])}"
    elif params['type'] == "chat":
        return render_twitch_chat(title, user_info['display_name'])

    if params['quality'] not in {"chunked", "auto"}:
        if params['type'] == "live":
            available_qualities = twitch_get_live_stream_qualities(params['channel'])
        elif params['type'] in {'vod', 'vodid'}:
            available_qualities = twitch_get_vod_stream_qualities(vodid)
        quality_result = twitch_get_final_stream_quality(params['quality'], available_qualities)
        params['quality'] = twitch_add_framerate_to_final_quality(quality_result)

    if params['type'] == "live":
        content_param = {'channel': user_info.get('login_name', params['channel'])}
    elif params['type'] in {'vod', 'vodid'}:
        content_param = {'video': vodid}
    else:
        content_param = {}

    player_params = {
        **content_param,  # Unpacks either 'channel' or 'video'
        **({'t': params['t']} if params['t'] else {}),
        'enableExtensions': params['extensions'],
        'parent': 'localhost',
        'player': 'popout',
        'quality': params['quality'],
        'muted': params['muted'],
        'volume': params['volume']
    }

    return renderer_helper('twitch', title, f"https://player.twitch.tv?{urlencode(player_params)}")

@app.route('/clip')
def twitch_clip_player():
    """Handle Twitch clips with query parameters"""
    # Check for runStreamledge flag
    if request.args.get('runStreamledge', '').lower() in ('1', 'true'):
        return run_in_streamledge('clip')
    
    clip_id = request.args.get('id')
    if not clip_id:
        return error_page("Missing clip ID parameter", 400)

    update_config(request.args.get('config') or streamledge.config_utils.CONFIG_PATH)
    
    clip_info = twitch_get_clip_info(clip_id)
    if clip_info:
        title = f"[CLIP] {clip_info['display_name']} - {clip_info['clip_title']}"
    else:
        title = "Twitch Clip"
    
    params = urlencode({
        'clip': clip_id,
        'parent': 'localhost',
        'player': 'popout',
        'quality': 'source',
        'muted': 0,
        'volume': 1,
        'autoplay': 1
    })

    player_url = f"https://clips.twitch.tv/embed?{params}"

    return renderer_helper('twitch', title, player_url)

### * KICK SECTION * ###

@lru_cache(maxsize=None)
def kick_get_user_info(username, max_retries=3):
    url = f"https://kick.com/api/v2/channels/{username.lower()}"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                impersonate="chrome120",
                timeout=(3.05, 5.0),
                headers={
                    'Accept': 'application/json',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            )
            
            if response.status_code == 404:
                print(f"User '{username}' not found")
                return None
                
            response.raise_for_status()
            
            data = response.json()
            return {
                'display_name': data['user']['username'],
                'user_id': data['user']['id'],
            }
            
        except requests.exceptions.HTTPError as e:
            if attempt == max_retries - 1:
                print(f"HTTP Error after {max_retries} attempts: {e}")
                return None
            time.sleep(1 * (attempt + 1))
            
        except json.JSONDecodeError as e:
            if attempt == max_retries - 1:
                print(f"Failed to parse JSON after {max_retries} attempts: {e}")
                return None
            time.sleep(1 * (attempt + 1))
            
        except KeyError as e:
            if attempt == max_retries - 1:
                print(f"Missing expected key after {max_retries} attempts: {e}")
                return None
            time.sleep(1 * (attempt + 1))
            
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Unexpected error after {max_retries} attempts: {e}")
                return None
            time.sleep(1 * (attempt + 1))
    
    return None

def kick_get_latest_vodid(username, max_retries=3):
    url = f"https://kick.com/api/v2/channels/{username}/videos/latest"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                impersonate="chrome120",
                timeout=(3.05, 5.0),
                headers={
                    'Accept': 'application/json',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            )
            
            if response.status_code == 404:
                print(f"No VODs found for user '{username}'")
                return None
                
            response.raise_for_status()
            
            vod_data = response.json()
            if vod_data.get('data', {}).get('video', {}).get('uuid'):
                return str(vod_data['data']['video']['uuid'])
                
            print(f"No valid VOD data in response (attempt {attempt + 1})")
            if attempt == max_retries - 1:
                return None
            time.sleep(1 * (attempt + 1))
            
        except requests.exceptions.HTTPError as e:
            if attempt == max_retries - 1:
                print(f"HTTP Error after {max_retries} attempts: {e}")
                return None
            time.sleep(1 * (attempt + 1))
            
        except json.JSONDecodeError as e:
            if attempt == max_retries - 1:
                print(f"Failed to parse JSON after {max_retries} attempts: {e}")
                return None
            time.sleep(1 * (attempt + 1))
            
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Unexpected error after {max_retries} attempts: {e}")
                return None
            time.sleep(1 * (attempt + 1))
    
    return None

@app.route('/kick')
def kick_player():
    """Handle both live and VOD Kick content with query parameters"""
    # Check for runStreamledge flag
    if request.args.get('runStreamledge', '').lower() in ('1', 'true'):
        return run_in_streamledge('kick')

    channel = request.args.get('channel')
    if not channel:
        return error_page("Missing channel parameter", 400)

    update_config(request.args.get('config') or streamledge.config_utils.CONFIG_PATH)

    # Get user info
    user_info = kick_get_user_info(channel)
    if not user_info:
        return error_page(f"Error: Kick user '{channel}' not found.", 400)

    # Determine content type (default to live)
    content_type = request.args.get('contentType', 'live').lower()
    
    if content_type == 'vod':
        # Handle VOD content
        vodid = kick_get_latest_vodid(channel)
        if not vodid:
            return error_page("Error: No VOD found for this channel", 400)
        player_url = f"https://kick.com/{channel}/videos/{vodid}"
        title = f"[VOD] {user_info['display_name']}"
    else:
        # Default to live content
        player_url = f"https://player.kick.com/{channel}"
        title = user_info['display_name']

    # Muted handling
    muted = config.get_service_setting('Kick', 'muted')
    if muted is None:
        muted = config.MUTED
    use_muted = request.args.get('muted', str(muted)).lower() in ('1', 'true')
    if use_muted:
        player_url += f"?muted=true"

    return renderer_helper('kick', title, player_url)

@app.route('/shutdown', strict_slashes=False)
def shutdown_route():
    shutdown_server()
    return "Server is shutting down..."

def main():
    if is_port_in_use(ACTIVE_PORT):
        print(f"Port {ACTIVE_PORT} is in use. Server will not start.")
        time.sleep(1.6)
        sys.exit(1)
    print(f"Streamledge Server {streamledge.config_utils.VERSION}")
    app.run(port=ACTIVE_PORT, threaded=True)
    sys.exit(0)

if __name__ == "__main__":
    main()