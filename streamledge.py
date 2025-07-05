import sys
import os
import time
import argparse
import subprocess
import socket
import re
import psutil
from config_utils import get_script_dir, initialize_config

script_dir = get_script_dir()
config_path = os.path.join(script_dir, 'config.ini')
config = initialize_config(config_path)
browser_profile_dir = os.path.join(script_dir, 'BrowserProfile')

DEFAULT_PORT = int(config['Server']['port'])
WINDOW_WIDTH = int(config['Browser']['width'])
WINDOW_HEIGHT = int(config['Browser']['height'])
WINDOW_X_POS = int(config['Browser']['x_pos'])
WINDOW_Y_POS = int(config['Browser']['y_pos'])
SERVER_NAMES = [
    'streamledge_server.exe',  # Compiled Windows
    'streamledge_server.py'   # Python script
]

def find_browser():
    # Check config first
    config_browser_path = config.get('Browser', 'browser_path', fallback='').strip()
    if config_browser_path and os.path.exists(config_browser_path):
        return config_browser_path
    paths = [
        os.path.expandvars("%PROGRAMFILES(X86)%\\Microsoft\\Edge\\Application\\msedge.exe"),
        os.path.expandvars("%PROGRAMFILES%\\Microsoft\\Edge\\Application\\msedge.exe"),
        os.path.expandvars("%LOCALAPPDATA%\\Microsoft\\Edge\\Application\\msedge.exe")
    ]
    
    for path in paths:
        if os.path.exists(path):
            return path
    
    # If we get here, no browser was not found
    print("\nERROR: Microsoft Edge not found in standard locations:")
    print(" - Program Files (x86)")
    print(" - Program Files")
    print(" - Local AppData")
    print("\nPlease install Microsoft Edge or specify the full path to a Chromium based browser in config.ini. Example:\n")
    print("[Browser]")
    print("browser_path = C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe")
    sys.exit(1)

def open_browser(port, type, info):
    browser_path = find_browser()
    url = f"http://localhost:{port}/{type}/{info}"
    edge_flags = [
        # ===== CORE SETTINGS =====
        browser_path,
        f"--app={url}",
        f"--user-data-dir={browser_profile_dir}",
        
        # ===== WINDOW CONTROL =====
        f"--window-size={WINDOW_WIDTH},{WINDOW_HEIGHT}",
        f"--window-position={WINDOW_X_POS},{WINDOW_Y_POS}",
        "--disable-features=WindowPlacement,NWNewWindow,WindowsOcclusion",
        "--enable-features=OverrideSiteSettings",
        
        # ===== VIDEO PERFORMANCE =====
        "--enable-parallel-downloading",
        "--enable-zero-copy",
        "--ignore-gpu-blocklist",
        
        # ===== PREFERENCE CONTROL =====
        "--no-first-run",
        "--no-default-browser-check",
        
        # ===== STABILITY FLAGS =====
        "--disable-logging",
        "--disable-breakpad"
    ]

    # Launch Browser
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                edge_flags,
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:  # untested
            subprocess.Popen(
                edge_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
    except Exception as e:
        print(f"Failed to launch web browser: {e}")
        sys.exit(1)

def kill_server_process():
    current_pid = os.getpid()
    killed = False
    found_processes = []

    # First collect all matching processes
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.pid == current_pid:
                continue

            proc_name = proc.name().lower()
            cmdline = [c.lower() for c in proc.cmdline()]

            # Check for matching process by name or command line
            is_target = False
            for server_name in SERVER_NAMES:
                if proc_name == server_name.lower():
                    is_target = True
                    break
                if any(server_name.lower() in c for c in cmdline):
                    is_target = True
                    break

            if is_target:
                found_processes.append(proc)

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    # Then handle all found processes
    if found_processes:
        print("Found running Streamledge server - terminating...")
        
        for proc in found_processes:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                    killed = True
                except psutil.TimeoutExpired:
                    proc.kill()
                    killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed:
            print("Streamledge server has been stopped")
    else:
        print("No running Streamledge server found")

    return killed

def find_server_path():
    base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
    
    for name in SERVER_NAMES:
        possible_path = os.path.join(base_dir, name)
        if os.path.exists(possible_path):
            return possible_path
    
    raise FileNotFoundError("Could not find Streamledge server executable/script in directory")

def start_server_process():
    try:
        server_path = find_server_path()
        
        if getattr(sys, 'frozen', False):
            # Running as compiled launcher - launch server with config
            args = [
                server_path
            ]
        else:
            # Running as Python script
            if server_path.endswith('.py'):
                args = [sys.executable, server_path]
            else:
                args = [server_path]
        
        # Launch process
        if sys.platform == 'win32':
            proc = subprocess.Popen(
                args,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:  # untested
            proc = subprocess.Popen(
                args,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        
        # Verify startup
        time.sleep(0.1)
        if proc.poll() is None:  # Process is still running
            print(f"Streamledge server started on port {DEFAULT_PORT}")
            return True
            
        print("Streamledge server process failed to start")
        return False
        
    except FileNotFoundError as e:
        print(f"Streamledge server executable not found: {e}")
        return False
    except Exception as e:
        print(f"Failed to start Streamledge server: {e}")
        return False

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.1)
        return s.connect_ex(('localhost', port)) == 0

def extract_youtube_id(input_str):
    # Patterns for various YouTube URL formats
    patterns = [
        r'(?:v=|\/embed\/|\/shorts\/|youtu\.be\/)([A-Za-z0-9_-]{11})',
        r'^([A-Za-z0-9_-]{11})$'  # plain ID
    ]
    for pattern in patterns:
        match = re.search(pattern, input_str)
        if match:
            return match.group(1)
    return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Streamledge Player')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--start', action='store_true', help='Start Streamledge server')
    group.add_argument('--stop', action='store_true', help='Close Streamledge server')
    group.add_argument('--live', metavar='CHANNEL', nargs='+', help='Twitch channel name(s) to play live stream')
    group.add_argument('--vod', metavar='CHANNEL', nargs='+', help='Twitch channel name(s) to play most recent VOD')
    group.add_argument('--yt', metavar='ID/URL', nargs='+', help='YouTube video ID(s) or URL(s) to play')
    
    args = parser.parse_args()

    if args.stop:
        if not kill_server_process():
            script_name = os.path.basename(__file__)
            exe_name = os.path.basename(sys.executable)
            display_name = exe_name if getattr(sys, 'frozen', False) else script_name
            print(f"No running Streamledge server found for {display_name}")
        sys.exit(0)

    if not is_port_in_use(DEFAULT_PORT):
        start_server_process()
    elif args.start:
        print(f"Port {DEFAULT_PORT} is in use.")
        sys.exit(0)

    if args.live:
        for channel in args.live:
            open_browser(DEFAULT_PORT, 'twitch', channel)
        if len(args.live) == 1:
            print(f"Launched browser app window of live Twitch stream: {args.live[0]}")
        else:
            print(f"Launched browser app windows of live Twitch streams: {', '.join(args.live)}")
    elif args.vod:
        for channel in args.vod:
            open_browser(DEFAULT_PORT, 'twitchvod', channel)
        if len(args.vod) == 1:
            print(f"Launched browser app window of VOD for Twitch channel: {args.vod[0]}")
        else:
            print(f"Launched browser app windows of VODs for Twitch channels: {', '.join(args.vod)}")
    elif args.yt:
        valid_ids = []
        for entry in args.yt:
            yt_id = extract_youtube_id(entry)
            if yt_id:
                open_browser(DEFAULT_PORT, 'youtube', yt_id)
                valid_ids.append(yt_id)
        if not valid_ids:
            print("Error: No valid YouTube video ID found in arguments.")
            sys.exit(1)
        elif len(valid_ids) == 1:
            print(f"Launched browser app window for YouTube ID: {valid_ids[0]}")
        else:
            print(f"Launched browser app windows for {len(valid_ids)} YouTube videos")

    sys.exit(0)