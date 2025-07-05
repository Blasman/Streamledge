import os
import re
import sys
import time
import socket
from functools import lru_cache
from urllib.parse import urlencode
import requests
from flask import Flask, render_template
from config_utils import get_script_dir, initialize_config

script_dir = get_script_dir()
config_path = os.path.join(script_dir, 'config.ini')
config = initialize_config(config_path)

app = Flask(__name__, template_folder='templates')

CLIENT_ID = config['Twitch']['client_id']
CLIENT_SECRET = config['Twitch']['client_secret']
DEFAULT_PORT = int(config['Server']['port'])

twitch_access_token = None
twitch_token_expires = 0

def get_twitch_access_token():
    global twitch_access_token, twitch_token_expires
    
    # Return existing token if still valid for at least 1 hour
    if twitch_access_token and time.time() < twitch_token_expires - 3600:
        return twitch_access_token
    
    # Only refresh if truly needed
    auth_url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    
    try:
        response = requests.post(auth_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        twitch_access_token = data['access_token']
        # Set expiration to 90% of actual time to be safe
        twitch_token_expires = time.time() + (data['expires_in'] * 0.9)
        return twitch_access_token
    except Exception as e:
        print(f"Token refresh failed: {e}")
        return twitch_access_token if twitch_access_token else None  # Return old token if available

def get_headers():
    return {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {get_twitch_access_token()}'
    }

def get_browser_dimensions():
    config = initialize_config(config_path)
    w = int(config['Browser']['width'])
    h = int(config['Browser']['height'])
    x = int(config['Browser']['x_pos'])
    y = int(config['Browser']['y_pos'])
    return w, h, x, y

@lru_cache(maxsize=None)
def get_twitch_user_info(username):
    try:
        url = f"https://api.twitch.tv/helix/users?login={username.lower()}"
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        data = response.json()
        
        if data['data']:
            return {
                'display_name': data['data'][0]['display_name'],
                'user_id': data['data'][0]['id']
            }
        return None
    except Exception as e:
        print(f"Couldn't fetch user info: {e}")
        return None

def get_latest_vod_id(user_id):
    try:
        if not user_id:
            print("Error: No user ID provided")
            return None

        vod_data = requests.get(
            f"https://api.twitch.tv/helix/videos?user_id={user_id}&type=archive&first=1",
            headers=get_headers()
        ).json().get("data", [])
        
        if not vod_data:
            print("Error: No VODs found")
            return None

        return vod_data[0]["id"]
    except Exception as e:
        print(f"API Error: {e}")
        return None

def is_valid_youtube_id(video_id):
    if len(video_id) != 11:
        return False
    pattern = r'^[a-zA-Z0-9_-]{11}$'
    return re.match(pattern, video_id) is not None

def get_youtube_title(video_id):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        return re.search(r'"title":"(.*?)"', response.text).group(1)
    except:
        return "YouTube Video"

@app.route('/youtube/<video_or_channel>')
def youtube_player(video_or_channel):
    title = get_youtube_title(video_or_channel) or "YouTube Video"
    params = urlencode({
        'autoplay': 1,
        'modestbranding': 1,
        'rel': 0,
        'fs': 1
    })

    if is_valid_youtube_id(video_or_channel):
        player_url = f"https://www.youtube.com/embed/{video_or_channel}?{params}"
    else:
        return "Error: Invalid YouTube video ID", 400

    width, height, x_pos, y_pos = get_browser_dimensions()
    
    return render_template('play_video.html',
        platform='youtube',
        icon_file='icons/youtube.ico',
        player_title=title,
        player_url=player_url,
        width=width,
        height=height,
        x_pos=x_pos,
        y_pos=y_pos
    )

@app.route('/twitch/<channel>')
def live_player(channel):
    user_info = get_twitch_user_info(channel)
    if not user_info:
        return f"Error: Twitch user '{channel}' not found.", 404
    params = {
        'channel': channel,
        'enableExtensions': 'true',
        'parent': 'localhost',
        'player': 'popout',
        'quality': 'chunked',
        'muted': 'false',
        'volume': '1'
    }
    player_url = f"https://player.twitch.tv/?{urlencode(params)}"
    width, height, x_pos, y_pos = get_browser_dimensions()

    return render_template('play_video.html',
        platform='twitch',
        icon_file='icons/twitch.ico',
        player_title=user_info['display_name'],
        player_url=player_url,
        width=width,
        height=height,
        x_pos=x_pos,
        y_pos=y_pos
    )

@app.route('/twitchvod/<channel>')
def vod_player(channel):
    user_info = get_twitch_user_info(channel)
    if not user_info:
        return f"Error: Twitch user '{channel}' not found.", 404
    vod_id = get_latest_vod_id(user_info['user_id'])
    if not vod_id:
        return "Error: No VOD found for this channel", 404
    params = {
        'video': vod_id,
        'enableExtensions': 'true',
        'parent': 'localhost',
        'player': 'popout',
        'quality': 'chunked',
        'muted': 'false',
        'volume': '1',
        'autoplay': 'true'
    }
    player_url = f"https://player.twitch.tv/?{urlencode(params)}"
    width, height, x_pos, y_pos = get_browser_dimensions()

    return render_template('play_video.html',
        platform='twitch',
        icon_file='icons/twitch.ico',
        player_title=f"[VOD] {user_info['display_name']}",
        player_url=player_url,
        width=width,
        height=height,
        x_pos=x_pos,
        y_pos=y_pos
    )

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.1)
        return s.connect_ex(('localhost', port)) == 0

if __name__ == "__main__":
    if is_port_in_use(DEFAULT_PORT):
        print(f"Error: Port {DEFAULT_PORT} is already in use. Server will not start.")
        sys.exit(1)
    app.run(port=DEFAULT_PORT, threaded=True)
    sys.exit(0)