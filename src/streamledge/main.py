import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from urllib.parse import quote, urlencode

from streamledge import config_utils
from streamledge.config_utils import AppConfig, get_window_position, initialize_config

def get_service_or_default_window_settings(service, config):    
    height = config.get_service_setting(service, 'display_area_height') or config.WINDOW_HEIGHT
    x_pos = config.get_service_setting(service, 'x_pos') or config.WINDOW_X_POS
    y_pos = config.get_service_setting(service, 'y_pos') or config.WINDOW_Y_POS
    return height, x_pos, y_pos

def base_url_to_service(base_url):
    if base_url in {'youtube', 'youtube_search'}: return 'YouTube'
    elif base_url in {'twitch', 'clip'}: return 'Twitch'
    elif base_url == 'kick': return 'Kick'
    return None

def open_browser(base_url, url_info, args, config, override_args=None):
    """Works with both CLI args and Flask calls by using override_args"""
    effective_args = override_args if override_args is not None else args

    # Browser path selection (works with both dict and Namespace)
    browser_path = (
        effective_args.get('browser_path') if isinstance(effective_args, dict)
        else getattr(effective_args, 'browser_path', config.BROWSER_PATH)
    ) or config.BROWSER_PATH
    
    browser_name = os.path.splitext(os.path.basename(browser_path))[0]

    # User data dir (works with both dict and Namespace)
    data_dir = (
        effective_args.get('data_dir') if isinstance(effective_args, dict)
        else getattr(effective_args, 'data_dir', config.USER_DATA_DIR)
    ) or config.USER_DATA_DIR

    browser_profile_dir = os.path.join(data_dir, f'{browser_name}-user-data')

    # Build optional params (works with both dict and Namespace)
    optional_params = []
    for param in ['height', 'x', 'y']:
        value = (
            effective_args.get(param) if isinstance(effective_args, dict)
            else getattr(effective_args, param, None)
        )
        if value:
            param_name = 'height' if param == 'height' else f'{param}_pos'
            optional_params.append(f"{param_name}={value}")

    # Modified config path handling (works with both dict and Namespace)
    config_path = None
    if isinstance(effective_args, dict):
        config_path = effective_args.get('config')
    else:
        config_path = getattr(effective_args, 'config', None)
    
    if config_path:
        normalized_path = str(config_path).replace('\\', '/')
        encoded_config = quote(normalized_path, safe='')
        optional_params.append(f"config={encoded_config}")

    if optional_params:
        separator = "&" if "?" in url_info else "?"
        url_info += separator + "&".join(optional_params)

    url = f"http://localhost:{config.PORT}/{base_url}{url_info}"

    url_only = (
        effective_args.get('url_only') if isinstance(effective_args, dict)
        else getattr(effective_args, 'url_only', False)
    )
    if url_only:
        print(url)
        return

    service = base_url_to_service(base_url)
    config_height, config_x_pos, config_y_pos = get_service_or_default_window_settings(service, config)
    height = (
        effective_args.get('height') if isinstance(effective_args, dict)
        else getattr(effective_args, 'height', config_height)
    ) or config_height

    width = round(height * 16 / 9)
    height = height + config.WINDOW_TITLEBAR_HEIGHT
    
    x_pos = (
        effective_args.get('x') if isinstance(effective_args, dict)
        else getattr(effective_args, 'x', config_x_pos)
    ) or config_x_pos
    
    y_pos = (
        effective_args.get('y') if isinstance(effective_args, dict)
        else getattr(effective_args, 'y', config_y_pos)
    ) or config_y_pos

    should_center_x_pos = config.WINDOW_CENTER_X_POS and config.get_service_setting(service, 'x_pos') is None
    should_center_y_pos = config.WINDOW_CENTER_Y_POS and config.get_service_setting(service, 'y_pos') is None

    if should_center_x_pos or should_center_y_pos:
        x_pos, y_pos = get_window_position(
            height=height,
            width=width,
            default_x_pos=x_pos,
            default_y_pos=y_pos,
            center_x=should_center_x_pos,
            center_y=should_center_y_pos
        )

    browser_flags = [
        browser_path,
        f"--app={url}",
        f"--user-data-dir={browser_profile_dir}",
        f"--window-size={width},{height}",
        f"--window-position={x_pos},{y_pos}",
        "--no-first-run",
        "--no-default-browser-check",
        "--autoplay-policy=no-user-gesture-required",
        *config.BROWSER_ARGS
    ]

    print(f"SERVING URL: {url}")

    try:
        subprocess.Popen(
            browser_flags,
            creationflags=subprocess.CREATE_NO_WINDOW if config_utils.WINDOWS_OS else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"Failed to launch web browser: {e}")

def just_browse(args, config, url=None):
    browser_path = args.browser_path or config.BROWSER_PATH
    browser_name = os.path.splitext(os.path.basename(browser_path))[0]
    data_dir = args.data_dir or config.USER_DATA_DIR
    browser_profile_dir = os.path.join(data_dir, f'{browser_name}-user-data')
    browser_flags = [
        browser_path,
        f"--user-data-dir={browser_profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--autoplay-policy=no-user-gesture-required",
        *config.BROWSER_ARGS
    ]
    if url and isinstance(url, str):
        browser_flags.append(url)
    try:
        subprocess.Popen(
            browser_flags,
            creationflags=subprocess.CREATE_NO_WINDOW if config_utils.WINDOWS_OS else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"Failed to launch web browser: {e}")

def shutdown_server(config):
    print("Attempting shutdown via /shutdown endpoint...")
    try:
        with socket.create_connection(("127.0.0.1", config.PORT), timeout=2) as sock:
            sock.sendall(b"GET /shutdown HTTP/1.1\r\nHost: localhost\r\n\r\n")
            response = sock.recv(1024)
            if b"200 OK" in response:
                print("✅ Server shutdown request successfully sent")
                return True
            else:
                print(f"⚠️ Unexpected response: {response.decode(errors='ignore')}")
    except Exception as e:
        print(f"❌ Raw socket shutdown failed: {e}")
    print(f"No running streamledge_server found on port {config.PORT}")
    return False

def start_server_process(config):
    try:
        # Try to locate the installed CLI command
        server_path = shutil.which("streamledge_server")
        if server_path:
            args = [server_path]
        else:
            # Fallback to running as a module
            args = [sys.executable, "-m", "streamledge_server.main"]

        # Start the process with platform-specific options
        if config_utils.WINDOWS_OS:
            proc = subprocess.Popen(
                args,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            proc = subprocess.Popen(
                args,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        # Wait for server to open its port
        timeout = 5
        interval = 0.1
        waited = 0
        while waited < timeout:
            if is_port_in_use(config.PORT):
                message = f"streamledge_server started on port {config.PORT}"
                if getattr(config, 'SERVER_SELF_DESTRUCT', False):
                    message += " and will self destruct"
                print(message)
                return True
            if proc.poll() is not None:
                print("streamledge_server process exited unexpectedly.")
                return False
            time.sleep(interval)
            waited += interval

        print("streamledge_server process failed to start (port not open).")
        return False

    except Exception as e:
        print(f"Failed to start streamledge_server: {e}")
        return False

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.1)
        return s.connect_ex(('localhost', port)) == 0

def parse_timestamp_to_seconds(timestamp):
    if timestamp.isdigit():
        return int(timestamp)
    pattern = r'^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$'
    match = re.match(pattern, timestamp)
    if not match or not any(match.groups()):
        raise ValueError(f"Invalid timestamp format: '{timestamp}'")
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    return hours * 3600 + minutes * 60 + seconds

def youtube_extract_video_id(input_str):
    video_id = None
    start_time = 0
    if isinstance(input_str, list):
        if not input_str:
            return (None, None)
        input_str = input_str[0]
    clean_str = str(input_str).strip()
    if clean_str.startswith('RD') and len(clean_str) == 13:
        potential_id = clean_str[2:]
        if re.match(r'^[0-9A-Za-z_-]{11}$', potential_id):
            return (potential_id, None)
    time_patterns = [
        r'[?&]t=(\d+h\d+m\d+s|\d+h\d+m|\d+h\d+s|\d+m\d+s|\d+h|\d+m|\d+s|\d+)',
        r'[?&]start=(\d+)',
        r'[?&]time_continue=(\d+)'
    ]
    for pattern in time_patterns:
        match = re.search(pattern, clean_str)
        if match:
            try:
                start_time = parse_timestamp_to_seconds(match.group(1))
                break
            except ValueError:
                pass
    patterns = [
        r'(?:v=|/embed/|/v/|/shorts/|youtu\.be/|\\?v=)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$',
        r'list=RD([0-9A-Zaz_-]{11})',
        r'list=RDMM([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, clean_str)
        if match:
            potential_id = match.group(1)
            if len(potential_id) == 11 and re.match(r'^[0-9A-Za-z_-]{11}$', potential_id):
                video_id = potential_id
                break
    return (video_id, start_time)

def youtube_extract_playlist_id(input_str):
    if isinstance(input_str, list):
        if not input_str:
            return None
        input_str = input_str[0]
    patterns = [
        r'(?:[/?&](?:list|p)=)([0-9A-Za-z_-]{13,34})(?:$|&)',
        r'(?:youtube\.com/playlist/)([0-9A-Za-z_-]{13,34})(?:$|/)',
        r'(?:youtube\.com/watch\?.*&list=)([0-9A-Za-z_-]{13,34})',
        r'^(PL[0-9A-Za-z_-]{32})$',
        r'^(RD[0-9A-Za-z_-]{11,34})$',
        r'^(OL[0-9A-Za-z_-]{32})$',
        r'^(UU[0-9A-Za-z_-]{32})$',
        r'^(FL[0-9A-Za-z_-]{32})$'
    ]
    clean_str = str(input_str).strip()
    for pattern in patterns:
        match = re.search(pattern, clean_str, re.IGNORECASE)
        if match:
            playlist_id = match.group(1)
            if (len(playlist_id) == 34 and playlist_id.startswith(('PL','OL','UU','FL'))) or \
               (len(playlist_id) in {13, 34, 36} and playlist_id.startswith('RD')):
                return playlist_id
    return None

def youtube_build_url(info, args, start_time=0):
    params = {}
    if getattr(args, 'autoplay', None) is not None:
        params['autoplay'] = 1 if args.autoplay else 0
    if getattr(args, 'autoclose', None) is not None:
        params['autoclose'] = 1 if args.autoclose else 0
    if getattr(args, 'fullscreen', None) is not None:
        params['fullscreen'] = 1 if args.fullscreen else 0
    if getattr(args, 'shuffle', None) is not None:
        params['shuffle'] = 1 if args.shuffle else 0
    if getattr(args, 'muted', None) is not None:
        params['muted'] = 1 if args.muted else 0
    if getattr(args, 'loop', None) is not None:
        params['loop'] = 1 if args.loop else 0
    if getattr(args, 'cc', None) is not None:
        params['cc'] = 1 if args.cc else 0
    if getattr(args, 'video_controls', None) is not None:
        params['video_controls'] = 1 if args.video_controls else 0
    if getattr(args, 'keyboard', None) is not None:
        params['keyboard'] = 1 if args.keyboard else 0
    if getattr(args, 'fsbutton', None) is not None:
        params['fsbutton'] = 1 if args.fsbutton else 0
    if getattr(args, 'vidstart', None) is not None:
        try:
            params['startTime'] = parse_timestamp_to_seconds(str(args.vidstart))
        except Exception:
            pass
    elif start_time > 0:
        params['startTime'] = start_time
    if getattr(args, 'ytpl', None) is not None and getattr(args, 'plstart', None) is not None:
        params['plstart'] = args.plstart
    if not params:
        return info
    encoded_params = urlencode(params)
    return info + '&' + encoded_params

# lazy color initialization (only set up when needed to avoid startup cost)
RESET = ""
BRIGHT_GREEN = ""
GREEN = ""
CYAN = ""
_colors_initialized = False

def init_colors():
    """Initialize terminal color sequences on demand."""
    global RESET, BRIGHT_GREEN, GREEN, CYAN, _colors_initialized
    if _colors_initialized:
        return
    try:
        import colorama
        colorama.init()
        RESET = colorama.Style.RESET_ALL
        BRIGHT_GREEN = colorama.Style.BRIGHT + colorama.Fore.GREEN
        GREEN = colorama.Fore.GREEN
        CYAN = colorama.Fore.CYAN
    except Exception:
        RESET = "\033[0m"
        BRIGHT_GREEN = "\033[1m\033[32m"
        GREEN = "\033[32m"
        CYAN = "\033[36m"
    # If output is not a terminal, disable color sequences
    try:
        import sys as _sys
        if not _sys.stdout.isatty():
            RESET = BRIGHT_GREEN = GREEN = CYAN = ""
    except Exception:
        pass
    _colors_initialized = True

def _color(text, code):
    # if not initialized, return plain text (avoids side effects)
    if not _colors_initialized:
        return text
    return f"{code}{text}{RESET}" if code else text

def youtube_search(query, search_type="both"):
    """Fetch YouTube search results using ytInitialData JSON when possible.
    Returns video entries with 'duration' and playlist entries with 'title' only.
    search_type: 'video' | 'playlist' | 'both'."""
    from urllib.parse import quote_plus
    import json
    import html
    import re

    def _find_playlist_count_from_html(page_html, plid):
        """Return integer count or None. Scans ytInitialData JSON first, then falls back to regex."""
        if not page_html:
            return None
        pdata = extract_json_initial_data(page_html)
        def _extract_int_from_value(val):
            try:
                if isinstance(val, (int, float)):
                    return int(val)
                if isinstance(val, str):
                    v = val.replace(",", "").strip()
                    if v.isdigit():
                        return int(v)
                return None
            except Exception:
                return None

        def _extract_count_from_node(node):
            # look for numeric fields
            if isinstance(node, dict):
                for key in ("videoCount", "itemCount", "count", "totalVideoCount", "numVideos", "videosCount"):
                    if key in node:
                        c = _extract_int_from_value(node.get(key))
                        if isinstance(c, int):
                            return c
                # look for text fields containing "videos"
                for key in ("videoCountText", "shortBylineText", "countText", "statsText", "description"):
                    if key in node:
                        txt = _extract_text_from_obj(node.get(key))
                        m = re.search(r'([0-9][0-9,]*)\s+videos?', txt or "", re.IGNORECASE)
                        if m:
                            try:
                                return int(m.group(1).replace(",", ""))
                            except Exception:
                                pass
                # check title/name adjacent strings
                for v in node.values():
                    res = _extract_count_from_node(v)
                    if res:
                        return res
            elif isinstance(node, list):
                for it in node:
                    res = _extract_count_from_node(it)
                    if res:
                        return res
            elif isinstance(node, str):
                m = re.search(r'([0-9][0-9,]*)\s+videos?', node, re.IGNORECASE)
                if m:
                    try:
                        return int(m.group(1).replace(",", ""))
                    except Exception:
                        pass
            return None

        # locate node with matching playlistId first (more reliable)
        if pdata:
            def find_node_with_playlist_id(node):
                if isinstance(node, dict):
                    try:
                        if node.get("playlistId") == plid:
                            return node
                    except Exception:
                        pass
                    for v in node.values():
                        found = find_node_with_playlist_id(v)
                        if found:
                            return found
                elif isinstance(node, list):
                    for it in node:
                        found = find_node_with_playlist_id(it)
                        if found:
                            return found
                return None
            node = find_node_with_playlist_id(pdata)
            if node:
                c = _extract_count_from_node(node)
                if c and c >= 1:
                    return c
            # fallback: search entire JSON for any "N videos" text
            c = _extract_count_from_node(pdata)
            if c and c >= 1:
                return c

        # final fallback: regex on HTML
        m2 = re.search(r'([0-9][0-9,]*)\s+videos?', page_html, re.IGNORECASE)
        if m2:
            try:
                parsed = int(m2.group(1).replace(",", ""))
                if parsed >= 1:
                    return parsed
            except Exception:
                pass
        return None


    def _extract_text_from_obj(obj):
        if not obj:
            return ""
        if isinstance(obj, str):
            return obj
        if isinstance(obj, dict):
            if "simpleText" in obj and isinstance(obj["simpleText"], str):
                return obj["simpleText"]
            if "text" in obj and isinstance(obj["text"], str):
                return obj["text"]
            if "runs" in obj and isinstance(obj["runs"], list):
                return "".join(r.get("text", "") for r in obj["runs"]).strip()
            if "title" in obj:
                return _extract_text_from_obj(obj["title"])
        return ""

    def extract_json_initial_data(s: str):
        key = "ytInitialData"
        idx = s.find(key)
        if idx == -1:
            return None
        start = s.find("{", idx)
        if start == -1:
            return None
        depth = 0
        i = start
        end = None
        while i < len(s):
            ch = s[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
            i += 1
        if end is None:
            return None
        json_text = s[start:end+1]
        try:
            return json.loads(json_text)
        except Exception:
            return None

    def walk_node(node, collect):
        if isinstance(node, dict):
            if "videoRenderer" in node:
                collect.append(("video", node["videoRenderer"]))
            if "playlistRenderer" in node:
                collect.append(("playlist", node["playlistRenderer"]))
            if "playlistId" in node:
                title_candidate = node.get("title") or node.get("name") or node.get("shortBylineText") or node.get("titleText")
                collect.append(("playlist", {"playlistId": node.get("playlistId"), "title_obj": title_candidate}))
            for v in node.values():
                walk_node(v, collect)
        elif isinstance(node, list):
            for item in node:
                walk_node(item, collect)

    q = quote_plus(query)
    if search_type == "playlist":
        url = f"https://www.youtube.com/results?search_query={q}&sp=EgIQAw%3D%3D"
    else:
        url = f"https://www.youtube.com/results?search_query={q}"

    # lazy fetch (curl-cffi preferred)
    try:
        from curl_cffi import requests as curl_requests
        resp = curl_requests.get(url, timeout=8)
        html_text = resp.text or ""
    except Exception:
        try:
            from urllib.request import urlopen
            with urlopen(url, timeout=8) as r:
                html_text = r.read().decode("utf-8", "ignore")
        except Exception as e:
            print(f"Failed to fetch YouTube search results: {e}")
            return []

    results = []

    # Try JSON-based extraction first
    data = extract_json_initial_data(html_text)
    if data:
        found = []
        walk_node(data, found)
        seen_ids = set()
        for kind, renderer in found:
            try:
                if kind == "video" and search_type in ("video", "both"):
                    vid = renderer.get("videoId")
                    if not vid or vid in seen_ids:
                        continue
                    title_obj = renderer.get("title") or renderer.get("titleText") or {}
                    title = _extract_text_from_obj(title_obj) or vid
                    duration = None
                    if "lengthText" in renderer:
                        duration = _extract_text_from_obj(renderer.get("lengthText")) or None
                    if not duration and "thumbnailOverlays" in renderer:
                        for overlay in renderer.get("thumbnailOverlays", []):
                            txt = _extract_text_from_obj(overlay.get("thumbnailOverlayTimeStatusRenderer", {}).get("text"))
                            if txt:
                                duration = txt
                                break
                    # robust uploader extraction
                    uploader_obj = (
                        renderer.get("ownerText")
                        or renderer.get("shortBylineText")
                        or renderer.get("longBylineText")
                        or renderer.get("videoOwnerText")
                        or renderer.get("byline")
                        or {}
                    )
                    uploader = _extract_text_from_obj(uploader_obj) or None
                    title = html.unescape(title)
                    uploader = html.unescape(uploader) if uploader else None
                    results.append({"type": "video", "id": vid, "title": title, "duration": duration, "uploader": uploader})
                    seen_ids.add(vid)

                elif kind == "playlist" and search_type in ("playlist", "both"):
                    plid = None
                    title = ""
                    uploader = None
                    if isinstance(renderer, dict):
                        plid = renderer.get("playlistId")
                        title_obj = renderer.get("title") or renderer.get("titleText") or renderer.get("shortBylineText") or renderer.get("name") or renderer.get("title_obj")
                        title = _extract_text_from_obj(title_obj)
                        # try to capture playlist owner/uploader from common fields
                        uploader_obj = (
                            renderer.get("shortBylineText")
                            or renderer.get("ownerText")
                            or renderer.get("longBylineText")
                            or renderer.get("byline")
                            or {}
                        )
                        uploader = _extract_text_from_obj(uploader_obj) or None
                    if not plid:
                        continue
                    if plid in seen_ids:
                        continue
                    title = html.unescape(title) or ""
                    uploader = html.unescape(uploader) if uploader else None
                    results.append({"type": "playlist", "id": plid, "title": title, "uploader": uploader})
                    seen_ids.add(plid)
            except Exception:
                continue

    # fallback: HTML regex extraction if JSON path yields nothing
    if not results:
        if search_type in ("video", "both"):
            for m in re.finditer(
                r'(<a[^>]+href="/watch\?v=([0-9A-Za-z_-]{11})[^"]*"[^>]*>.*?</a>)',
                html_text, re.IGNORECASE | re.DOTALL
            ):
                full_tag = m.group(1)
                vid = m.group(2)
                title_attr = re.search(r'title="([^"]+)"', full_tag)
                if title_attr:
                    title = html.unescape(title_attr.group(1).strip())
                else:
                    inner = re.sub(r'<[^>]+>', '', full_tag).strip()
                    title = html.unescape(inner) if inner else vid
                results.append({"type": "video", "id": vid, "title": title, "duration": None})
                if len(results) >= 50:
                    break
        if search_type in ("playlist", "both"):
            seen = {r.get("id") for r in results}
            for m in re.finditer(
                r'(<a[^>]+href="/playlist\?list=([^"&]+)[^"]*"[^>]*>.*?</a>)',
                html_text, re.IGNORECASE | re.DOTALL
            ):
                full_tag = m.group(1)
                plid = m.group(2)
                title_attr = re.search(r'title="([^"]+)"', full_tag)
                if title_attr:
                    title = html.unescape(title_attr.group(1).strip())
                else:
                    inner = re.sub(r'<[^>]+>', '', full_tag).strip()
                    title = html.unescape(inner) if inner else plid
                if plid not in seen:
                    results.append({"type": "playlist", "id": plid, "title": title})
                    seen.add(plid)
                if len(results) >= 50:
                    break

    # Post-process: use oEmbed for titles only (no counts)
    try:
        from curl_cffi import requests as _curl_requests
    except Exception:
        _curl_requests = None

    # Fast oEmbed for videos (only top 10) to get clean titles (oEmbed doesn't provide duration)
    if search_type in ("video", "both"):
        for item in [r for r in results if r['type'] == 'video'][:10]:
            # skip if we already have a reasonable title
            if item.get('title'):
                continue
            vid = item.get('id')
            if not vid:
                continue
            try:
                oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json"
                if _curl_requests is not None:
                    resp = _curl_requests.get(oembed_url, timeout=3)
                    if getattr(resp, "status_code", 0) == 200:
                        j = resp.json()
                        if j.get("title"):
                            item['title'] = html.unescape(j.get("title"))
                        if j.get("author_name"):
                            item['uploader'] = html.unescape(j.get("author_name"))
                else:
                    from urllib.request import urlopen, Request
                    req = Request(oembed_url, headers={"User-Agent": "python"})
                    with urlopen(req, timeout=3) as r:
                        import json as _json
                        j = _json.loads(r.read().decode("utf-8", "ignore"))
                        if j.get("title"):
                            item['title'] = html.unescape(j.get("title"))
                        if j.get("author_name"):
                            item['uploader'] = html.unescape(j.get("author_name"))
            except Exception:
                continue

    # For playlists: only use oEmbed for title/uploader fallback (no counts previously)
    if search_type in ("playlist", "both"):
        to_fix = [r for r in results if r['type'] == 'playlist' and (not r.get('title') or not r.get('uploader') or not isinstance(r.get('count'), int))][:10]
        for item in to_fix:
            plid = item.get('id')
            if not plid:
                continue
            # oEmbed for title/uploader (no auth needed)
            try:
                oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/playlist?list={plid}&format=json"
                if _curl_requests is not None:
                    r = _curl_requests.get(oembed_url, timeout=3)
                    if getattr(r, "status_code", 0) == 200:
                        j = r.json()
                        if j.get("title"):
                            item['title'] = html.unescape(j.get("title").strip())
                        if j.get("author_name"):
                            item['uploader'] = html.unescape(j.get("author_name"))
                else:
                    from urllib.request import urlopen, Request
                    req = Request(oembed_url, headers={"User-Agent": "python"})
                    with urlopen(req, timeout=3) as ph:
                        import json as _json
                        j = _json.loads(ph.read().decode("utf-8", "ignore"))
                        if j.get("title"):
                            item['title'] = html.unescape(j.get("title").strip())
                        if j.get("author_name"):
                            item['uploader'] = html.unescape(j.get("author_name"))
            except Exception:
                pass

            # Try lightweight playlist page fetch for count (top 10 only)
            try:
                page_url = f"https://www.youtube.com/playlist?list={plid}"
                page_html = ""
                if _curl_requests is not None:
                    p = _curl_requests.get(page_url, timeout=6)
                    page_html = p.text or ""
                else:
                    from urllib.request import urlopen, Request
                    req = Request(page_url, headers={"User-Agent": "python"})
                    with urlopen(req, timeout=6) as ph:
                        page_html = ph.read().decode("utf-8", "ignore")
                if page_html:
                    cnt = _find_playlist_count_from_html(page_html, plid)
                    if isinstance(cnt, int) and cnt >= 1:
                        item['count'] = cnt
            except Exception:
                pass

    return results

def twitch_extract_username(input_str, special_type=None):
    if special_type == 'vod':
        if ':' in input_str and not input_str.endswith(':'):
            base_input, vod_num = input_str.rsplit(':', 1)
            if vod_num.isdigit():
                username = twitch_extract_username(base_input)
                if username:
                    return f"{username}:{vod_num}"
        return twitch_extract_username(input_str)
    patterns = [
        r'twitch\.tv/([a-zA-Z0-9_]{4,25})(?:\?|$|/)',
        r'twitch\.tv/([a-zA-Z0-9_]{4,25})/(?:videos|clips|v|about|schedule|events|collections|subscriptions)(?:\?|$|/)',
        r'(?:embed|player)\.twitch\.tv\?(?:[^&]*&)*channel=([a-zA-Z0-9_]{4,25})(?:&|$)',
        r'twitch\.tv/([a-zA-Z0-9_]{4,25})/clip/',
        r'^([a-zA-Z0-9_]{4,25})(?::\d+)?$',
        r'login=([a-zA-Z0-9_]{4,25})(?:&|$)',
        r'([a-zA-Z0-9_]{4,25})\.twitch\.tv',
        r'twitch\.tv/moderator/([a-zA-Z0-9_]{4,25})',
        r'twitch\.tv/popout/([a-zA-Z0-9_]{4,25})',
        r'twitch\.tv/([a-zA-Z0-9_]{4,25})/dashboard'
    ]
    for pattern in patterns:
        match = re.search(pattern, input_str, re.IGNORECASE)
        if match:
            username = match.group(1).lower()
            return username
    return None

def twitch_extract_clip_ip(input_str):
    patterns = [
        r'twitch\.tv/[^/]+/clip/([a-zA-Z0-9_-]+)(?:[?/]|$)',
        r'clips\.twitch\.tv/(?!embed\?)([a-zA-Z0-9_-]+)(?:[?/]|$)',
        r'clips\.twitch\.tv/embed\?clip=([a-zA-Z0-9_-]+)(?:&|$)',
        r'player\.twitch\.tv/\?(?:.*&)?clip=([a-zA-Z0-9_-]+)(?:&|$)',
        r'^([a-zA-Z0-9_-]+)$'
    ]
    clean_str = input_str.strip()
    for pattern in patterns:
        match = re.search(pattern, clean_str, re.IGNORECASE)
        if match:
            clip_id = match.group(1)
            if re.fullmatch(r'^[a-zA-Z0-9_-]+$', clip_id):
                return clip_id
    return None

def twitch_get_timestamp_from_vod_url(input_str):
    match = re.search(r'[?&]t=((?:\d+h)?(?:\d+m)?(?:\d+s)?)', input_str)
    if match and match.group(1):
        return match.group(1)
    return None

def twitch_extract_vodid(input_str):
    patterns = [
        r'twitch\.tv/videos/(\d+)(?:\?|$|/)',
        r'twitch\.tv/[^/]+/videos\?(?:[^&]*&)*video=(\d+)(?:&|$)',
        r'twitch\.tv/[^/]+/v/(\d+)(?:\?|$|/)',
        r'(?:embed|player)\.twitch\.tv\?(?:[^&]*&)*video=(\d+)(?:&|$)',
        r'^(\d+)$',
        r'twitch\.tv/[^/]+/(?:b|c)/(\d+)(?:\?|$|/)',
        r'(?:video=|v=)(\d+)(?:&|$)'
    ]
    for pattern in patterns:
        match = re.search(pattern, input_str, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def twitch_open_chat(query_string, args, config, override_args=None):
    effective_args = override_args if override_args is not None else args
    url = f"http://localhost:{config.PORT}/twitch{query_string}"
    if getattr(effective_args, 'url_only', False):
        print(url)
        return
    browser_path = (
        effective_args.get('browser_path') if isinstance(effective_args, dict)
        else getattr(effective_args, 'browser_path', config.BROWSER_PATH)
    ) or config.BROWSER_PATH
    browser_name = os.path.splitext(os.path.basename(browser_path))[0]
    data_dir = (
        effective_args.get('data_dir') if isinstance(effective_args, dict)
        else getattr(effective_args, 'data_dir', config.USER_DATA_DIR)
    ) or config.USER_DATA_DIR
    browser_profile_dir = os.path.join(data_dir, f'{browser_name}-user-data')
    optional_params = []
    for param in ['height', 'x', 'y']:
        value = (
            effective_args.get(param) if isinstance(effective_args, dict)
            else getattr(effective_args, param, None)
        )
        if value:
            param_name = 'height' if param == 'height' else f'{param}_pos'
            optional_params.append(f"{param_name}={value}")
    url_info = ''
    if optional_params:
        separator = "&" if "?" in url_info else "?"
        url_info += separator + "&".join(optional_params)
    def get_twitch_chat_setting(setting, default):
        value = config.get_service_setting('Twitch', setting)
        try:
            return int(value) if value is not None else default
        except ValueError:
            return default
    config_height = get_twitch_chat_setting('chat_height', config.TWITCH_CHAT_HEIGHT)
    config_width = get_twitch_chat_setting('chat_width', config.TWITCH_CHAT_WIDTH)
    x_pos = get_twitch_chat_setting('chat_x_pos', config.TWITCH_CHAT_X_POS)
    y_pos = get_twitch_chat_setting('chat_y_pos', config.TWITCH_CHAT_Y_POS)
    height = (
        effective_args.get('height') if isinstance(effective_args, dict)
        else getattr(effective_args, 'height', config_height)
    ) or config_height
    width = (
        effective_args.get('width') if isinstance(effective_args, dict)
        else getattr(effective_args, 'width', config_width)
    ) or config_width
    height = height + config.WINDOW_TITLEBAR_HEIGHT
    should_center_x_pos = config.TWITCH_CENTER_CHAT_X_POS and config.get_service_setting('Twitch', 'chat_x_pos') is None
    should_center_y_pos = config.TWITCH_CENTER_CHAT_Y_POS and config.get_service_setting('Twitch', 'chat_y_pos') is None
    if should_center_x_pos or should_center_y_pos:
        x_pos, y_pos = get_window_position(
            height=config_height,
            width=config_width,
            default_x_pos=x_pos,
            default_y_pos=y_pos,
            center_x=should_center_x_pos,
            center_y=should_center_y_pos
        )
    browser_flags = [
        browser_path,
        f"--app={url}",
        f"--user-data-dir={browser_profile_dir}",
        f"--window-size={width},{height}",
        f"--window-position={x_pos},{y_pos}",
        "--no-first-run",
        "--no-default-browser-check",
        "--autoplay-policy=no-user-gesture-required",
        *config.BROWSER_ARGS
    ]
    print(f"SERVING URL: {url}")
    try:
        subprocess.Popen(
            browser_flags,
            creationflags=subprocess.CREATE_NO_WINDOW if config_utils.WINDOWS_OS else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"Failed to launch web browser: {e}")

def twitch_build_url(channel_or_vodid, content_type, args, start_time=None):
    params = []
    if not args.live:
        params.append(f"contentType={content_type}")
    vods_ago = getattr(args, 'vodsAgo', None)
    if ':' in channel_or_vodid and args.vod:
        base_channel, vods_ago_str = channel_or_vodid.split(':', 1)
        try:
            vods_ago = int(vods_ago_str)
        except ValueError:
            vods_ago = 1
        channel_or_vodid = base_channel
    if args.live or args.vod or args.chat:
        params.append(f"channel={channel_or_vodid}")
        if args.vod and vods_ago is not None:
            params.append(f"vodsAgo={vods_ago}")
    if args.vodid:
        params.append(f"vodid={channel_or_vodid}")
    if args.vod or args.vodid:
        if args.vodstart:
            params.append(f"vodStart={args.vodstart}")
        elif start_time:
            params.append(f"vodStart={start_time}")
    if args.quality:
        params.append(f"quality={args.quality}")
    if args.muted is not None:
        params.append(f"muted={'1' if args.muted else '0'}")
    if args.volume is not None:
        params.append(f"volume={args.volume}")
    if args.extensions is not None:
        params.append(f"enableExtensions={'1' if args.extensions else '0'}")
    return "?" + "&".join(params)

def twitch_handle_entries(entries, content_type, args, config):
    valid_entries = []
    extractor = {
        'live': twitch_extract_username,
        'vod': lambda x: twitch_extract_username(x, special_type='vod'),
        'vodid': twitch_extract_vodid,
        'chat': twitch_extract_username
    }.get(content_type)
    if not extractor:
        return valid_entries
    for entry in entries:
        entry_start_time = None
        if content_type == 'vodid':
            entry_start_time = twitch_get_timestamp_from_vod_url(entry)
        identifier = extractor(entry)
        if identifier:
            url = twitch_build_url(identifier, content_type, args, entry_start_time)
            if content_type != 'chat':
                open_browser('twitch', url, args, config)
            else:
                twitch_open_chat(url, args, config)
            valid_entries.append(identifier)
    return valid_entries

def kick_extract_username(input_str):
    patterns = [
        r'kick\.com/([a-zA-Z0-9_]{3,25})(?:\?|$|/)',
        r'kick\.com/([a-zA-Z0-9_]{3,25})/(?:videos|clip|about)(?:\?|$|/)',
        r'^([a-zA-Z0-9_]{3,25})$',
        r'kick\.com/embed/chat\?(?:[^&]*&)*channel=([a-zA-Z0-9_]{3,25})(?:&|$)',
        r'kick\.com/([a-zA-Z0-9_]{3,25})/clip/',
        r'kick\.com/api/v1/channels/([a-zA-Z0-9_]{3,25})',
        r'kick\.com/video/(?:[a-f0-9-]+)\?channel=([a-zA-Z0-9_]{3,25})'
    ]
    for pattern in patterns:
        match = re.search(pattern, input_str, re.IGNORECASE)
        if match:
            username = match.group(1).lower()
            return username
    return None

def main():
    parser = argparse.ArgumentParser(description=f'Streamledge {config_utils.VERSION}')
    main_exclusive = parser.add_mutually_exclusive_group()
    main_exclusive.add_argument('--start', action='store_true', help='Start streamledge_server background process (NOT STRICTLY REQUIRED - happens automatically if needed)')
    main_exclusive.add_argument('--stop', action='store_true', help='Close streamledge_server background process')

    def validate_config_file(path: str) -> str:
        """Validate config file path and handle both full paths and local files."""
        path = path.strip('"\'')  # Clean quotes
        
        # Try as direct path first
        if os.path.isabs(path):
            if not os.path.exists(path):
                raise argparse.ArgumentTypeError(f"Config file not found at: {path}")
        else:
            # Try local path
            local_path = os.path.join(os.getcwd(), path)
            if os.path.exists(local_path):
                path = local_path
            else:
                raise argparse.ArgumentTypeError(f"Config file not found at: {path} (tried {local_path})")
        
        if not os.path.isfile(path):
            raise argparse.ArgumentTypeError(f"Path is not a file: {path}")
        if not os.access(path, os.R_OK):
            raise argparse.ArgumentTypeError(f"Config file is not readable: {path}")
        
        return os.path.abspath(path)

    def validate_browser_path(path: str) -> str:
        """Validate the browser executable path."""
        path = path.strip('"\'')  # Clean quotes
        if not path:
            raise argparse.ArgumentTypeError("Browser path cannot be empty")
        if not os.path.exists(path):
            raise argparse.ArgumentTypeError(f"Browser executable not found at: {path}")
        if not os.path.isfile(path):
            raise argparse.ArgumentTypeError(f"Path is not a file: {path}")
        if not os.access(path, os.X_OK):
            raise argparse.ArgumentTypeError(f"File is not executable: {path}")
        
        return os.path.abspath(path)  # Return normalized path
    
    def validate_user_data_dir(dir_path: str) -> str:
        """Strict validation for user data directory (no auto-creation)."""
        dir_path = dir_path.strip('"\'').rstrip(os.sep)  # Clean path
        if not dir_path:
            raise argparse.ArgumentTypeError("Directory path cannot be empty")
        if not os.path.exists(dir_path):
            raise argparse.ArgumentTypeError(f"Directory does not exist '{dir_path}' Please create it first.")
        if not os.path.isdir(dir_path):
            raise argparse.ArgumentTypeError(f"Path is not a directory: {dir_path}")
        # Check read/write permissions
        if not os.access(dir_path, os.R_OK | os.W_OK):
            raise argparse.ArgumentTypeError(f"Insufficient permissions for directory: {dir_path}")
        
        return os.path.abspath(dir_path)  # Return normalized path

    def validate_youtube_timestamp(value):
        # Accept either a pure number (seconds) or a composite time string
        if re.match(r'^\d+$', value):
            return value  # Pure seconds, like "90"
    
        pattern = r'^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$'
        match = re.match(pattern, value)
        if not match or not any(match.groups()):
            raise argparse.ArgumentTypeError("Time format must be like '90' or '1h2m3s'")
        
        return value

    def validate_twitch_timestamp(value):
        pattern = r'^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$'
        match = re.match(pattern, value)
        if not match or value == '':
            raise argparse.ArgumentTypeError("Time format must be like '1h2m3s'")
    
        return value  # Return the original string unchanged

    # Argument parser
    optional_group = parser.add_argument_group('Player/Browser options')
    optional_group.add_argument('--config', metavar='PATH',
        type=validate_config_file,
        help='Path to alternate config file (either full path or filename in current directory)')
    optional_group.add_argument('--height', '--size', type=int, metavar='HEIGHT',
        help='Set display area height of web browser window')
    optional_group.add_argument('--x', type=int, metavar='X_POS',
        help='Set X position of browser window')
    optional_group.add_argument('--y', type=int, metavar='Y_POS',
        help='Set Y position of browser window')
    optional_group.add_argument('--browser-path', metavar='PATH',
        type=validate_browser_path,  # validation
        help='Full path to Chromium-based browser executable')
    optional_group.add_argument('--data-dir', metavar='DIR',
        type=validate_user_data_dir,  # validation
        help='Base dir for generated user data directory')
    optional_group.add_argument('--muted', type=int, choices=[0, 1], nargs='?', const=1, default=None, metavar='0|1', 
        help='Begin playback muted')
    optional_group.add_argument('--url-only',
        action='store_true',
        help='Only display generated URL. Do not run Streamledge')
    
    # YouTube group
    youtube_group = parser.add_argument_group('YouTube.com options')
    
    # Add the exclusive group first
    youtube_exclusive = youtube_group.add_mutually_exclusive_group()
    youtube_exclusive.add_argument('--yt', metavar='VIDEO_ID(s)/URL(s)/QUERY', nargs='+',
                                help='Play YouTube video ID(s)/URL(s)/first search query result')
    youtube_exclusive.add_argument('--ytpl', metavar='PLAYLIST_ID/URL/QUERY', nargs='+',
                                help='Play YouTube playlist ID/URL/first search query result')
    youtube_exclusive.add_argument('--ytsearch', metavar='QUERY', nargs='+',
                             help='Search for videos and choose from the top 10 results')
    youtube_exclusive.add_argument('--ytplsearch', metavar='QUERY', nargs='+',
                              help='Search for playlists and choose from the top 10 results')
    youtube_exclusive.add_argument('--ytmix', metavar='VIDEO_ID/URL/QUERY', nargs='+',
                                help='Play YouTube generated Mix/Radio playlist from video')
    
    # Then add the non-exclusive options
    youtube_group.add_argument('--autoplay', type=int, choices=[0, 1], nargs='?', const=1, default=None, metavar='0|1', 
                             help='*OPTIONAL* Begin playback automaticaly')
    youtube_group.add_argument('--autoclose', type=int, choices=[0, 1], nargs='?', const=1, default=None, metavar='0|1', 
                             help='*OPTIONAL* Close window automatically when playback ends')
    if config_utils.WINDOWS_OS:
        youtube_group.add_argument('--fullscreen', '--fs', type=int, choices=[0, 1], nargs='?', const=1, default=None, metavar='0|1', 
                                 help='*OPTIONAL* Fullscreen video (auto mouse clicks window)')
    youtube_group.add_argument('--shuffle', type=int, choices=[0, 1], nargs='?', const=1, default=None, metavar='0|1', 
                             help='*OPTIONAL* Shuffle playlist order')
    youtube_group.add_argument('--loop', type=int, choices=[0, 1], nargs='?', const=1, default=None, metavar='0|1', 
                             help='*OPTIONAL* Toggle continuous playback looping')
    youtube_group.add_argument('--cc', type=int, choices=[0, 1], nargs='?', const=1, default=None, metavar='0|1', 
                             help='*OPTIONAL* Toggle closed captions on by default')
    youtube_group.add_argument('--video-controls', type=int, choices=[0, 1], nargs='?', const=1, default=None, metavar='0|1', 
                             help='*OPTIONAL* Toggle video controls')
    youtube_group.add_argument('--keyboard', type=int, choices=[0, 1], nargs='?', const=1, default=None, metavar='0|1', 
                             help='*OPTIONAL* Toggle keyboard controls')
    youtube_group.add_argument('--fsbutton', type=int, choices=[0, 1], nargs='?', const=1, default=None, metavar='0|1', 
                             help='*OPTIONAL* Toggle fullscreen button on GUI')
    youtube_group.add_argument('--vidstart', type=validate_youtube_timestamp, default=None, metavar='TIME',
                             help="*OPTIONAL* Begin video playback at timestamp like '120' for seconds or '1h2m3s' (automatically detected if in URL)")
    youtube_group.add_argument('--plstart', type=int, default=None, metavar='NUM',
                             help='*OPTIONAL* Begin/create playlist from the NUM video of playlist')

    # Twitch group
    twitch_group = parser.add_argument_group('Twitch.tv options')
    twitch_exclusive = twitch_group.add_mutually_exclusive_group()
    twitch_exclusive.add_argument('--live', '--twitch', metavar='CHANNEL/URL', nargs='+',
                                help='Play live stream of channel name(s)')
    twitch_exclusive.add_argument('--vod', metavar='CHANNEL[:N]/URL', nargs='+',
                                help='Play most recent VOD of channel name(s). Add :N for Nth most recent (e.g. username:2 for 2nd most recent)')
    twitch_exclusive.add_argument('--vodid', metavar='VOD ID/URL', nargs='+',
                                help='Play Twitch VOD for ID(s)/URL(s)')
    twitch_exclusive.add_argument('--clip', metavar='CLIP ID/URL', nargs='+',
                                help='Play Twitch clips for ID(s)/URL(s)')
    twitch_exclusive.add_argument('--chat', metavar='CHANNEL/URL', nargs='+',
                                help='Open chat of channel names(s)')
    
    def validate_volume(value):
        try:
            volume = int(value)
            if volume < 1 or volume > 100:
                raise argparse.ArgumentTypeError("Volume must be between 1 and 100")
            return volume
        except ValueError:
            raise argparse.ArgumentTypeError("Volume must be an integer between 1 and 100")
        
    twitch_group.add_argument('--volume', type=validate_volume, metavar='[1-100]',
                             help='*OPTIONAL* Volume level (1-100)')
    
    twitch_group.add_argument('--extensions', type=int, choices=[0, 1], nargs='?', const=1, default=None, metavar='0|1',
                             help='*OPTIONAL* Enable Twitch extensions on video')
        
    def validate_quality(value):
        """Validate that quality is either 'source'/'auto' or matches resolution like 720/720p/720p60.
        Supports comma-separated lists of qualities."""
        def validate_single_quality(q):
            q = q.lower().strip()
            
            if q in ('source', 'auto'):
                return q
        
            # Accept plain numbers like '480' or '1080'
            if re.fullmatch(r'\d+', q):
                return f"{q}p"
        
            # Accept formats like '720p' or '1080p60'
            if re.fullmatch(r'\d+p(60)?', q):
                return q
        
            raise argparse.ArgumentTypeError(
                f"Invalid quality '{q}'. Must be 'source', 'auto', or resolution like 720/720p/1080p60"
            )
    
        # Handle comma-separated list
        if ',' in value:
            qualities = [validate_single_quality(q) for q in value.split(',')]
            return ','.join(qualities)
        
        # Single quality case
        return validate_single_quality(value)

    twitch_group.add_argument(
        '--quality', type=validate_quality,
        help='*OPTIONAL* Preferred video qualitie(s) (comma-separated list). Use "source", "auto", or any resolution like "720p" or "1080p60"'
    )

    twitch_group.add_argument('--vodstart', type=validate_twitch_timestamp, default=None, metavar='TIME',
        help="*OPTIONAL* Begin VOD playback at timestamp like '1h2m3s' (automatically detected if in URL)"
    )

    # Kick group
    kick_group = parser.add_argument_group('Kick.com options')
    kick_exclusive = kick_group.add_mutually_exclusive_group()
    kick_exclusive.add_argument('--kick', metavar='CHANNEL/URL', nargs='+',
                              help='Play live stream of channel name(s)')
    kick_exclusive.add_argument('--kickvod', metavar='CHANNEL/URL', nargs='+',
                              help='Play most recent VOD of channel name(s)')

    # Misc group
    misc_group = parser.add_argument_group('Misc options')
    misc_exclusive = misc_group.add_mutually_exclusive_group()
    misc_exclusive.add_argument('--browse', metavar='URL', nargs='?', const=True,
                   help='Open browser normally (with optional URL). Install extensions, log in to Twitch, etc.')
    misc_exclusive.add_argument('--appdata', action='store_true', help='Open Streamledge appdata directory in file explorer')

    args = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    if args.shuffle and args.plstart:
        print(f"Don't use --shuffle and --plstart together. That makes no sense.")
        sys.exit(0)

    platform_args = sum([bool(args.start or args.stop),
                        bool(args.live or args.vod or args.vodid or args.clip or args.chat),
                        bool(args.kick or args.kickvod),
                        bool(args.yt or args.ytpl or args.ytmix or args.ytsearch or args.ytplsearch),
                        bool(args.browse or args.appdata)])
    if platform_args > 1:
        parser.error("Cannot combine platforms (Twitch/YouTube/Kick/Misc). Choose one.")

    default_config_exists = os.path.exists(config_utils.CONFIG_PATH)
    using_custom_config = bool(args.config)

    if args.config:  # also creates new config in none exist
        CONFIG = initialize_config(args.config)
    else:
        CONFIG = initialize_config(config_utils.CONFIG_PATH)
    config = AppConfig(CONFIG)

    if args.appdata:
        appdata_dir = config_utils.CONFIG_DIR
        print(f"Opening appdata directory: {appdata_dir}")
        try:
            if config_utils.WINDOWS_OS:
                os.startfile(appdata_dir)
            elif config_utils.MAC_OS:
                subprocess.Popen(['open', appdata_dir])
            else:
                subprocess.Popen(['xdg-open', appdata_dir])
        except Exception as e:
            print(f"Failed to open appdata directory: {e}")
        sys.exit(0)

    if not default_config_exists and not using_custom_config:
        print("You may try running streamledge again with the default configuration.")
        print("At any time, run 'sl --appdata' to open the folder containing your config.ini file.")
        sys.exit(0)

    if args.stop:
        shutdown_server(config)
        sys.exit(0)

    if not is_port_in_use(config.PORT):
        start_server_process(config)
    elif args.start:
        print(f"Port {config.PORT} is in use. Server will not start.")
        sys.exit(0)

    valid_entries = []
    if args.yt:
        any_invalid = False
        for entry in args.yt:
            result, start_time = youtube_extract_video_id(entry)
            if result:
                valid_entries.append(result)
            else:
                any_invalid = True
                break
        if any_invalid:
            if len(args.yt) == 1:
                playlist_id = youtube_extract_playlist_id(args.yt)
                if playlist_id:
                    open_browser('youtube', f"?id={(youtube_build_url(playlist_id, args))}", args, config)
                else:
                    search_query = ' '.join(args.yt)
                    open_browser('youtube_search', f"?q={(youtube_build_url(quote(search_query, safe=''), args))}", args, config)
            else:
                search_query = ' '.join(args.yt)
                open_browser('youtube_search', f"?q={(youtube_build_url(quote(search_query, safe=''), args))}", args, config)
        else:
            if len(valid_entries) == 1:
                open_browser('youtube', f"?id={(youtube_build_url(valid_entries[0], args, start_time))}", args, config)
            else:
                if len(valid_entries) > 200:
                    print(f"Warning: Truncating playlist to first 200 items (received {len(valid_entries)})")
                    valid_entries = valid_entries[:200]
                parsed_entries = ','.join(valid_entries)
                open_browser('youtube', f"?id={(youtube_build_url(parsed_entries, args))}", args, config)
    elif args.ytpl:
        result = False
        if len(args.ytpl) == 1:
            result = youtube_extract_playlist_id(args.ytpl)
        if not result:
            video_id, start_time = youtube_extract_video_id(args.ytpl)
            if video_id:
                open_browser('youtube', f"?id={(youtube_build_url(video_id, args, start_time))}", args, config)
            else:
                search_query = ' '.join(args.ytpl)
                open_browser('youtube_search', f"?searchType=playlist&q={(youtube_build_url(quote(search_query, safe=''), args))}", args, config)
        else:
            open_browser('youtube', f"?id={(youtube_build_url(result, args))}", args, config)
    elif args.ytsearch:
        parts = args.ytsearch
        query = " ".join(parts)
        print(f"Searching YouTube for: {query}")
        results = youtube_search(query, search_type="video")
        vids = [r for r in results if r['type'] == 'video']
        if not vids:
            print("No video results found.")
            sys.exit(0)
        init_colors()
        for i, it in enumerate(vids[:10], start=1):
            label = '0' if i == 10 else str(i)
            label_str = f"{_color(label, BRIGHT_GREEN)}{_color(')', GREEN)}"
            dur = it.get('duration') or ''
            if dur:
                dur_label = f" {_color('[', GREEN)}{_color(dur, BRIGHT_GREEN)}{_color(']', GREEN)}"
            else:
                dur_label = ""
            uploader = it.get('uploader')
            if uploader:
                print(f"{label_str} {it['title']}{dur_label} {_color(uploader, CYAN)}")
            else:
                print(f"{label_str} {it['title']}{dur_label}")
        sel = input("Choose a result to open (1-9,0=10) or press Enter to cancel: ").strip()
        if not sel:
            print("Cancelled.")
            sys.exit(0)
        if sel == '0':
            idx = 10
        elif sel.isdigit():
            idx = int(sel)
        else:
            print("Invalid selection.")
            sys.exit(1)
        if 1 <= idx <= min(10, len(vids)):
            chosen = vids[idx - 1]
            print(f"Opening: {chosen['title']}")
            open_browser('youtube', f"?id={(youtube_build_url(chosen['id'], args, 0))}", args, config)
            sys.exit(0)
        else:
            print("Selection out of range.")
            sys.exit(1)
    elif args.ytplsearch:
        parts = args.ytplsearch
        query = " ".join(parts)
        print(f"Searching YouTube for playlists: {query}")
        results = youtube_search(query, search_type="playlist")
        pls = [r for r in results if r['type'] == 'playlist']
        if not pls:
            print("No playlist results found.")
            sys.exit(0)
        init_colors()
        for i, it in enumerate(pls[:10], start=1):
            label = '0' if i == 10 else str(i)
            label_str = f"{_color(label, BRIGHT_GREEN)}{_color(')', GREEN)}"
            count = it.get('count')
            if isinstance(count, int):
                count_label = f" {_color('[', GREEN)}{_color(str(count), BRIGHT_GREEN)}{_color(']', GREEN)}"
            else:
                count_label = ""
            uploader = it.get('uploader')
            if uploader:
                print(f"{label_str} {it['title']}{count_label} {_color(uploader, CYAN)}")
            else:
                print(f"{label_str} {it['title']}{count_label}")
        sel = input("Choose a result to open (1-9,0=10) or press Enter to cancel: ").strip()
        if not sel:
            print("Cancelled.")
            sys.exit(0)
        if sel == '0':
            idx = 10
        elif sel.isdigit():
            idx = int(sel)
        else:
            print("Invalid selection.")
            sys.exit(1)
        if 1 <= idx <= min(10, len(pls)):
            chosen = pls[idx - 1]
            print(f"Opening playlist: {chosen['title']}")
            open_browser('youtube', f"?id={(youtube_build_url(chosen['id'], args))}", args, config)
            sys.exit(0)
        else:
            print("Selection out of range.")
    elif args.ytmix:
        result = False
        if len(args.ytmix) == 1:
            result, _ = youtube_extract_video_id(args.ytmix)
        if not result:
            search_query = ' '.join(args.ytmix)
            open_browser('youtube_search', f"?searchType=mix&q={(youtube_build_url(quote(search_query, safe=''), args))}", args, config)
        else:
            radio_id = f"RD{result}"
            open_browser('youtube', f"?id={(youtube_build_url(radio_id, args))}", args, config)
    elif args.live or args.vod:
        content_type = 'live' if args.live else 'vod'
        entries = args.live if args.live else args.vod
        valid_entries = twitch_handle_entries(entries, content_type, args, config)
        if not valid_entries:
            print("Error: No valid Twitch usernames found in arguments.")
    elif args.vodid:
        valid_entries = twitch_handle_entries(args.vodid, 'vodid', args, config)
        if not valid_entries:
            print("Error: No valid Twitch VOD ID found.")
    elif args.clip:
        for entry in args.clip:
            clip_id = twitch_extract_clip_ip(entry)
            if clip_id:
                open_browser('clip', f"?id={clip_id}", args, config)
                valid_entries.append(clip_id)
        if not valid_entries:
            print("Error: No valid Twitch clip ID found in arguments.")
    elif args.kick:
        for entry in args.kick:
            username = kick_extract_username(entry)
            if username:
                url = f"?channel={username}"
                if args.muted is not None:
                    url += f"&muted={'1' if args.muted else '0'}"
                open_browser('kick', url, args, config)
                valid_entries.append(username)
        if not valid_entries:
            print("Error: No valid Kick usernames found in arguments.")
    elif args.kickvod:
        for entry in args.kickvod:
            username = kick_extract_username(entry)
            if username:
                url = f"?channel={username}&contentType=vod"
                if args.muted is not None:
                    url += f"&muted={'1' if args.muted else '0'}"
                open_browser('kick', url, args, config)
                valid_entries.append(username)
        if not valid_entries:
            print("Error: No valid Kick usernames found in arguments.")
    elif args.browse:
        if isinstance(args.browse, bool):
            just_browse(args, config)
        else:
            just_browse(args, config, args.browse)
    elif args.chat:
        valid_entries = twitch_handle_entries(args.chat, 'chat', args, config)
        if not valid_entries:
            print("Error: No valid Twitch usernames found in arguments.")

    if getattr(config, 'SERVER_SELF_DESTRUCT', False):
        max_wait = 10
        waited = 1
        time.sleep(waited)
        while is_port_in_use(config.PORT) and waited < max_wait:
            time.sleep(0.1)
            waited += 0.1
        if waited >= max_wait:
            print(f"⚠️ Server port {config.PORT} still in use after {max_wait} seconds")
        else:
            print("streamledge_server has self destructed")
    sys.exit(0)

if __name__ == '__main__':
    main()