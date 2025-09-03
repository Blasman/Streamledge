import configparser
import os
import re
import sys
from typing import List
from platformdirs import user_config_dir

try:
    from importlib.metadata import version, PackageNotFoundError
except Exception:
    version = None
    PackageNotFoundError = Exception

VERSION = None

# 1) try installed distribution names
if version:
    for pkg in ("streamledge", "streamledge_temp"):
        try:
            v = version(pkg)
            if v:
                VERSION = f"v{str(v).lstrip('v')}"
                break
        except PackageNotFoundError:
            continue

# 2) fallback to CI/env refs like refs/tags/v1.2.3 or STREAMLEDGE_VERSION
if VERSION is None:
    env_ver = os.environ.get("STREAMLEDGE_VERSION") or os.environ.get("GITHUB_REF_NAME") or os.environ.get("GITHUB_REF")
    if env_ver:
        env_ver = str(env_ver).split("/")[-1].lstrip("v")
        VERSION = f"v{env_ver}"

# 3) final fallback
if VERSION is None:
    VERSION = "dev-version"

WINDOWS_OS = sys.platform == "win32"
LINUX_OS = sys.platform.startswith("linux")
MAC_OS = sys.platform == "darwin"

# import modules required for retrieving window coordinates
if WINDOWS_OS:
    import ctypes
    from ctypes import wintypes
elif LINUX_OS:
    import subprocess
elif MAC_OS:
    pass  #  ¯\_(ツ)_/¯

# Default/fallback config settings
DEFAULT_PORT = 5008
DEFAULT_SERVER_SELF_DESTRUCT = False
DEFAULT_DISPLAY_AREA_HEIGHT = 540
DEFAULT_WINDOWS_TITLEBAR_HEIGHT = 30  # best guess
DEFAULT_NON_WINDOWS_TITLEBAR_HEIGHT = 0  
DEFAULT_X_POS = 480
DEFAULT_Y_POS = 135
DEFAULT_MUTED = False
DEFAULT_TITLE_SUFFIX = False
DEFAULT_YOUTUBE_AUTOPLAY = True
DEFAULT_YOUTUBE_AUTOCLOSE = True
DEFAULT_YOUTUBE_FULLSCREEN = False
DEFAULT_YOUTUBE_SHUFFLE = False
DEFAULT_YOUTUBE_MUTED = False
DEFAULT_YOUTUBE_LOOP = False
DEFAULT_YOUTUBE_CC = False
DEFAULT_YOUTUBE_CONTROLS = True
DEFAULT_YOUTUBE_KEYBOARD = True
DEFAULT_YOUTUBE_FSBUTTON = True
DEFAULT_YOUTUBE_ANNOTATIONS = False
DEFAULT_YOUTUBE_NOCOOKIE = True
DEFAULT_YOUTUBE_LANGUAGE = ''
DEFAULT_YOUTUBE_UPDATE_TITLE = True

DEFAULT_TWITCH_VOLUME = 100
DEFAULT_TWITCH_EXTENSIONS = True
DEFAULT_TWITCH_QUALITY = "source"
DEFAULT_TWITCH_CHAT_HEIGHT = 99999
DEFAULT_TWITCH_CHAT_WIDTH = 600
DEFAULT_TWITCH_CHAT_X_POS = 99999
DEFAULT_TWITCH_CHAT_Y_POS = 0
DEFAULT_TWITCH_CHAT_DARK_MODE = True

if WINDOWS_OS:
    TITLEBAR_CONFIG = f"""
# Streamledge attempts to auto-detect windows titlebar_height. This is required info to draw a properly sized browser window.
# If you see any solid black color around the borders of the display area, then you may want to adjust your titlebar_height accordingly.
# To adjust or correctly set the height in pixels of your windows titlebars, uncomment the line below and set value.
# titlebar_height = {DEFAULT_WINDOWS_TITLEBAR_HEIGHT}
"""
    YOUTUBE_FULLSCREEN_CONFIG = f"""
# Automatically switch to fullscreen mode when playback begins. This is a bit of a gimmick.
# This simulates a double click on the video upon video playback and then moves/hides the mouse cursor back to its original position.
# Set to true/false
# Override with --fullscreen [0|1]
fullscreen = {DEFAULT_YOUTUBE_FULLSCREEN}
"""
else:
    TITLEBAR_CONFIG = ""
    YOUTUBE_FULLSCREEN_CONFIG = ""

if not MAC_OS:
    POS_COMMENT = """# Streamledge attempts to position the web browser window in the middle and closer to the top of your display.
# To manually set either of the X and/or Y position(s), uncomment the x_pos and/or y_pos lines below and set desired value(s)."""
else:
    POS_COMMENT = """# You may manually set either of the X and/or Y position(s).
# Uncomment the x_pos and/or y_pos lines below and set desired value(s). Otherwise, default values will be used."""

DEFAULT_CONFIG = f"""[Server]

# Network port for the local Streamledge flask web server background service. The default of '5008' should be fine.
port = {DEFAULT_PORT}

# Have the 'streamledge_server' process automatically terminate itself after serving content.
# Set to true/false
self_destruct = {DEFAULT_SERVER_SELF_DESTRUCT}

[Browser]

# Display area HEIGHT of the web browser window.
# Override with --height [num]
display_area_height = {DEFAULT_DISPLAY_AREA_HEIGHT}
{TITLEBAR_CONFIG}
{POS_COMMENT}
# Override with --x [num]  and/or  --y [num]
# x_pos = {DEFAULT_X_POS}
# y_pos = {DEFAULT_Y_POS}

# Streamledge searches your system for a suitable default chromium based web browser in order of preference:  MS Edge > Chrome > Chromium
# Optionally specify path to compatible chromium based web browser executable file by uncommenting the 'browser_path = ' line below.
# Override with --browser-path [path]
# browser_path = C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe

# By default, Streamledge creates the web browsers user data dir within Streamledge's --appdata dir.
# To use a different directory, uncomment the user_data_dir line below and set path.
# Override with --data-dir [dir]
# user_data_dir = 

# Optionally modify the chromium browser arguments used in addition to those already used/hardcoded in the commented line below.
# --app --user-data-dir --window-size --window-position --no-first-run --no-default-browser-check --autoplay-policy=no-user-gesture-required
arguments = 
    --enable-features=OverrideSiteSettings,ParallelDownloading,ZeroCopy
    --disable-features=WindowPlacement,NWNewWindow,WindowsOcclusion,PreloadMediaEngagementData
    --enable-zero-copy
    --enable-parallel-downloading
    --disable-logging
    --disable-breakpad
    --ignore-gpu-blocklist
# Problematic args:  --in-process-gpu  --disable-site-isolation-trials

# Begin playback of videos muted.
# Set to true/false
# Override with --muted [0|1]
muted = {DEFAULT_MUTED}

# Optionally add service name suffix to window title in the form of ' - ServiceName'. eg: false == "UserName"  vs  true == "UserName - Twitch"
title_suffix = {DEFAULT_TITLE_SUFFIX}

[YouTube]

# Automatically begin playback for videos/playlists.
# Set to true/false
# Override with --autoplay [0|1]
autoplay = {DEFAULT_YOUTUBE_AUTOPLAY}

# Automatically close the window when playback ends.
# Set to true/false
# Override with --autoclose [0|1]
autoclose = {DEFAULT_YOUTUBE_AUTOCLOSE}
{YOUTUBE_FULLSCREEN_CONFIG}
# Shuffle the *entire* playlist and return up to 200 results (200 is the limit for all embedded playlists).
# Set to true/false
# Override with --shuffle [0|1]
shuffle = {DEFAULT_YOUTUBE_SHUFFLE}

# Enable continuous playback looping.
# Set to true/false
# Override with --loop [0|1]
loop = {DEFAULT_YOUTUBE_LOOP}

# Enable closed captioning on by default.
# Set to true/false
# Override with --cc [0|1]
cc = {DEFAULT_YOUTUBE_CC}

# Enable/disable video controls.
# Set to true/false
# Override with --video-controls [0|1]
video_controls = {DEFAULT_YOUTUBE_CONTROLS}

# Enable/disable keyboard controls.
# Set to true/false
# Overrise with --keyboard [0|1]
keyboard = {DEFAULT_YOUTUBE_KEYBOARD}

# Enable/disable fullscreen button on GUI. Disabling the button also disables the ability to fullscreen.
# Set to true/false
# Override with --fsbutton [0|1]
fsbutton = {DEFAULT_YOUTUBE_FSBUTTON}

# Enable/disable video annotations. Effectiveness is questionable. 'nocookie' option below has this forcibly disabled.
# Set to true/false
annotations = {DEFAULT_YOUTUBE_ANNOTATIONS}

# Optionally play videos/playlists with 'youtube-nocookie.com' instead of 'youtube.com'.
# Set to true/false
nocookie = {DEFAULT_YOUTUBE_NOCOOKIE}

# Optionally set ISO 639-1 two-letter language code for YouTube GUI and preferred closed caption language.
# Reference: https://www.loc.gov/standards/iso639-2/php/code_list.php
# language = 

# Playlists only: Update the window titlebar with the name of the currently playing video.
# When 'true': Begin playback with the name of the playlist in the window titlebar until progressing to the next video.
# When 'false': Keeps the playlist name in the window titlebar at all times.
update_title = {DEFAULT_YOUTUBE_UPDATE_TITLE}

# Optionally override global [Browser] settings.
# display_area_height = 
# x_pos = 
# y_pos = 
# muted = 

[Twitch]

# Note that the following options (except 'extensions') are simply the loading values when playing a video.
# You can always use the cogwheel on the video to change these options at any time during playback.

# Default Twitch video_quality. You may specify *any* desired resolution with an optional 60 for 60fps.
# If specific video_quality is not available, then the next best option is used.
# Example: if 1080p is unavailable, then 720p60 is used rather than 1080p60. Therefor, be sure to specify the 60 if wanting 60fps.
# You may specify a comma-separated list of qualities in order of preference. ie: video_quality = 1080p, 720p, 1080p60, 720p60
# Common options: source | auto | 1080p60 | 1080p | 720p60 | 720p | 480p | 360p | 160p
# Override with --quality [quality]
video_quality = {DEFAULT_TWITCH_QUALITY}

# Set default volume percentage (1-100).
# Override with --volume [1-100]
volume = {DEFAULT_TWITCH_VOLUME}

# Enable Twitch extensions on the video overlay.
# Set to true/false
# Override with --extensions [0|1]
extensions = {DEFAULT_TWITCH_EXTENSIONS}

# Optionally override global [Browser] settings.
# display_area_height = 
# x_pos = 
# y_pos = 
# muted = 

# Optionally set size, loading position, and light/dark mode for --chat arg to open Twitch chat. (x and y will center if not set)
# Default settings will force the chat window to the right of the screen and utilize all screen space from top to bottom.
chat_height = {DEFAULT_TWITCH_CHAT_HEIGHT}
chat_width = {DEFAULT_TWITCH_CHAT_WIDTH}
chat_x_pos = {DEFAULT_TWITCH_CHAT_X_POS}
chat_y_pos = {DEFAULT_TWITCH_CHAT_Y_POS}
chat_dark_mode = {DEFAULT_TWITCH_CHAT_DARK_MODE}

[Kick]

# Optionally override global [Browser] settings.
# display_area_height = 
# x_pos = 
# y_pos = 
# muted = """

def get_titlebar_height():
    if not WINDOWS_OS:
        return DEFAULT_NON_WINDOWS_TITLEBAR_HEIGHT
    
    # This is a complete guess... it could be a placebo, but it appears to be working for different Windows OS setups...
    try:
        SM_CYCAPTION = 4
        SM_CYSIZEFRAME = 32
        SM_CXPADDEDBORDER = 92
        
        caption = ctypes.windll.user32.GetSystemMetrics(SM_CYCAPTION)
        frame = ctypes.windll.user32.GetSystemMetrics(SM_CYSIZEFRAME)
        padding = ctypes.windll.user32.GetSystemMetrics(SM_CXPADDEDBORDER)
        
        # This appears to be working. Not sure if it will work for all Windows OS setups.
        return caption + frame + padding - 1
    except (AttributeError, OSError):
        print(f"Warning: Title bar height detection failed. Using value of '{DEFAULT_WINDOWS_TITLEBAR_HEIGHT}' instead. Set [Browser] titlebar_height manually in config.ini.")
        return DEFAULT_WINDOWS_TITLEBAR_HEIGHT  # Fallback for Windows OS if API calls fail

def is_truthy_falsy(value):
    """Check if a string value represents a valid truthy/falsy value."""
    if not value.strip():  # Empty/whitespace is considered valid (no warning)
        return True
    return value.strip().lower() in ('true', 'false', '1', '0')

def is_nullish(config, section, key):
    """Returns True if key is missing, empty, or whitespace-only."""
    try:
        value = config.get(section, key)
        return not value.strip()  # True if empty or whitespace
    except configparser.NoOptionError:
        return True  # Missing key counts as nullish

def is_true(value):
    """Check if a string value evaluates to True."""
    if value is None or not str(value).strip():  # None or empty evaluates to False
        return False
    value = str(value).strip().lower()
    return value in ('true', '1')

def get_window_position(height, width, default_x_pos=DEFAULT_X_POS, default_y_pos=DEFAULT_Y_POS, center_x=False, center_y=False):
    try:
        if center_x or center_y:
            if WINDOWS_OS:
                user32 = ctypes.windll.user32
                screen_width = user32.GetSystemMetrics(0)
                screen_height = user32.GetSystemMetrics(1)
            elif LINUX_OS:
                try:
                    output = subprocess.check_output(
                        ['xrandr --current | grep " connected " | awk \'{print $4}\' | cut -d+ -f1'], 
                        shell=True
                    ).decode().strip()
                    if 'x' in output:
                        screen_width, screen_height = map(int, output.split('x'))
                except:
                    pass
    
            x_pos = max(0, round((screen_width - width) // 2)) if center_x else default_x_pos
            y_pos = max(0, round((screen_height - height) // 4)) if center_y else default_y_pos

            return x_pos, y_pos
        
    except Exception:
        pass

    return default_x_pos, default_y_pos

def get_valid_default_web_browser():
    browser_paths = []
    
    if WINDOWS_OS:
        # Microsoft Edge
        browser_paths.extend([
            os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge Beta\Application\msedge.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge Dev\Application\msedge.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge SxS\Application\msedge.exe"),
        ])

        # Google Chrome
        browser_paths.extend([
            os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome Beta\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome Dev\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome SxS\Application\chrome.exe"),
        ])

        # Chromium
        browser_paths.extend([
            os.path.expandvars(r"%LOCALAPPDATA%\Chromium\Application\chrome.exe"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Chromium\Application\chrome.exe"),
        ])

    elif LINUX_OS:
        browser_paths.extend([
            "/usr/bin/google-chrome",
            "/opt/google/chrome/chrome",
            "/usr/local/google-chrome/chrome",
            "/usr/local/chromium/chrome",
            os.path.expanduser("~/.var/app/com.google.Chrome/bin/google-chrome"),
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/snap/bin/chromium",
            "/usr/local/bin/chromium",
            os.path.expanduser("~/.var/app/org.chromium.Chromium/bin/chromium"),
            "/usr/bin/microsoft-edge",
        ])

    elif MAC_OS:
        browser_paths.extend([
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            os.path.expanduser("~/Applications/Chromium.app/Contents/MacOS/Chromium"),
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            os.path.expanduser("~/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
        ])

    for path in browser_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path

    return None

def is_valid_language_format(lang_code):
    pattern = r'^[a-zA-Z]{2,3}(-[a-zA-Z]{2,4})?$'
    return bool(re.fullmatch(pattern, lang_code))

def validate_config(config):
    warnings = []
    errors = []
    
    def service_override_settings(service):
        # Optional Browser overrides
        try:
            display_area_height = config.getint(service, 'display_area_height')
            if display_area_height <= 0:
                errors.append(f"[{service}] display_area_height must be a positive integer")
        except configparser.NoOptionError:
            pass
        except ValueError:
            errors.append(f"[{service}] display_area_height must be a valid integer")

        # Check for x_pos and y_pos
        for pos_key in ('x_pos', 'y_pos'):
            try:
                pos_str = config.get(service, pos_key).strip()
                if pos_str:  # Only validate non-empty strings
                    try:
                        if (pos := int(pos_str)) < 0:
                            errors.append(f"[{service}] {pos_key} must be a non-negative integer")
                    except ValueError:
                        errors.append(f"[{service}] {pos_key} must be a valid integer")
            except configparser.NoOptionError:
                pass

        # Validate muted
        try:
            muted = config.get(service, 'muted')
            if not is_truthy_falsy(muted):
                errors.append(f"[{service}] muted = '{muted}' is not a valid boolean value. Use 'true'/'false'")
        except configparser.NoOptionError:
            pass

    # Check Server section - info is required
    try:
        if not config.has_section('Server'):
            errors.append("Missing [Server] section in config.ini.")
        else:
            try:
                port = config.getint('Server', 'port')
                if not (1024 <= port <= 65535):
                    errors.append(f"Invalid port number '{port}'. Must be between 1024 and 65535")
            except configparser.NoOptionError:
                errors.append("[Server] port is missing.")
            except ValueError:
                errors.append("[Server] port must be a valid integer between 1024 and 65535")

            try:
                self_destruct = config.get('Server', 'self_destruct')
                if not is_truthy_falsy(self_destruct):
                    warnings.append(f"[Server] self_destruct = '{self_destruct}' is not a valid boolean value. Use 'true'/'false'. Using default of '{DEFAULT_SERVER_SELF_DESTRUCT}'")
            except configparser.NoOptionError:
                warnings.append(f"[Server] self_destruct not specified. Defaulting to '{DEFAULT_SERVER_SELF_DESTRUCT}'")

    except configparser.NoSectionError:
        errors.append("Missing [Server] section in config.ini.")
    
    # Check Browser section
    try:
        if not config.has_section('Browser'):
            errors.append("Missing [Browser] section in config.ini")
        else:
            try:
                display_area_height = config.getint('Browser', 'display_area_height')
                if display_area_height <= 0:
                    errors.append("[Browser] display_area_height must be a positive integer")
            except configparser.NoOptionError:
                warnings.append(f"[Browser] display_area_height is missing. Using default value of '{DEFAULT_DISPLAY_AREA_HEIGHT}'")
            except ValueError:
                errors.append("[Browser] display_area_height must be a valid integer")
    
            def can_get_screen_position():
                try:
                    if WINDOWS_OS:
                        ctypes.windll.user32.GetSystemMetrics(0)
                        return True
                    elif LINUX_OS:
                        output = subprocess.check_output(
                            ['xrandr', '--current'],
                            stderr=subprocess.DEVNULL
                        ).decode()
                        if " connected" in output:
                            return True
                except Exception:
                    pass
        
                return False

            # Check for x_pos and y_pos
            center_capable = can_get_screen_position()
            for pos_key, default_pos in [('x_pos', DEFAULT_X_POS), ('y_pos', DEFAULT_Y_POS)]:
                try:
                    pos_str = config.get('Browser', pos_key)
                    if not pos_str.strip():  # Empty/whitespace
                        if not center_capable:
                            warnings.append(f"Unable to center {pos_key} position. Please set [Browser] {pos_key}. Using default value of '{default_pos}'")
                    else:
                        try:
                            pos = int(pos_str)
                            if pos < 0:
                                errors.append(f"[Browser] {pos_key} must be a non-negative integer")
                        except ValueError:
                            errors.append(f"[Browser] {pos_key} must be a valid integer")
                except configparser.NoOptionError:
                    if not center_capable:
                        warnings.append(f"Unable to center {pos_key} position. Please set [Browser] {pos_key}. Using default value of '{default_pos}'")

            # Check browser_path if present and require it for non Windows OS
            try:
                # Get and clean the browser path
                browser_path = config.get('Browser', 'browser_path', fallback='').replace('"', '').strip()
                
                if not browser_path:
                    valid_browser = get_valid_default_web_browser()
                    if not valid_browser:
                        errors.append("No valid chromium based browsers found on system. Please specify path to one in config.ini")
                else:
                    # Additional checks for the path
                    if not os.path.exists(browser_path):
                        errors.append(f"[Browser] browser_path does not exist: {browser_path}")
                    elif not os.path.isfile(browser_path):  # Ensure it's a file
                        errors.append(f"[Browser] browser_path is not a file: {browser_path}")
                    elif not os.access(browser_path, os.X_OK):  # Check if executable
                        errors.append(f"[Browser] browser_path is not executable: {browser_path}")
            except configparser.NoOptionError:
                valid_browser = get_valid_default_web_browser()
                if not valid_browser:
                    errors.append("No valid chromium based browsers found on system. Please specify path to one in config.ini")
            except Exception as e:
                errors.append(f"[Browser] Error checking browser_path: {str(e)}")
    
            # Check user_data_dir if present
            try:
                user_data_dir = config.get('Browser', 'user_data_dir', fallback='').replace('"', '').strip()
                if user_data_dir:
                    if os.path.exists(user_data_dir):
                        if not os.path.isdir(user_data_dir):
                            errors.append(f"[Browser] user_data_dir is not a directory: {user_data_dir}")
                        elif not os.access(user_data_dir, os.R_OK | os.W_OK):
                            errors.append(f"[Browser] user_data_dir '{user_data_dir}' is not read/writable")
                    else:
                        errors.append(f"[Browser] user_data_dir '{user_data_dir}' does not exist. Please create it first.")
            except configparser.NoOptionError:
                pass
            except Exception as e:
                errors.append(f"[Browser] Error checking user_data_dir: {str(e)}")
    
            # Verify that any web browser arguments are at least in valid --arg format
            try:
                arguments = config.get('Browser', 'arguments', fallback='').strip()
                if arguments:  # Only check if non-empty
                    for line in arguments.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('--'):
                            errors.append(f"[Browser] Invalid argument: '{line}' (must start with --)")
                            break
            except configparser.NoOptionError:
                pass

            # Validate muted
            try:
                muted = config.get('Browser', 'muted')
                if not is_truthy_falsy(muted):
                    warnings.append(f"[Browser] muted = '{muted}' is not a valid boolean value. Use 'true'/'false'. Using default of '{DEFAULT_MUTED}'")
            except configparser.NoOptionError:
                warnings.append(f"[Browser] muted not specified. Defaulting to '{DEFAULT_MUTED}'")

            # Validate title_suffix - only warn if set to non-truthy/falsy value
            try:
                title_suffix = config.get('Browser', 'title_suffix')
                if not is_truthy_falsy(title_suffix):
                    warnings.append(f"[Browser] title_suffix = '{title_suffix}' is not a valid boolean value. Use 'true'/'false'. Defaulting to '{DEFAULT_TITLE_SUFFIX}'")
            except configparser.NoOptionError:
                warnings.append(f"[Browser] title_suffix not specified. Defaulting to '{DEFAULT_TITLE_SUFFIX}'")
    except configparser.NoSectionError:
        errors.append("Missing [Browser] section in config.ini")

    # Check YouTube section
    try:
        if not config.has_section('YouTube'):
            warnings.append(f"Missing [YouTube] section in config.ini. Using default values: autoplay='{DEFAULT_YOUTUBE_AUTOPLAY}', loop='{DEFAULT_YOUTUBE_LOOP}', shuffle='{DEFAULT_YOUTUBE_SHUFFLE}', fullscreen='{DEFAULT_YOUTUBE_FULLSCREEN}', autoclose='{DEFAULT_YOUTUBE_AUTOCLOSE}', update_title='{DEFAULT_YOUTUBE_UPDATE_TITLE}'")
        else:
            try:
                autoplay = config.get('YouTube', 'autoplay')
                if not is_truthy_falsy(autoplay):
                    warnings.append(f"[YouTube] autoplay = '{autoplay}' is not a valid boolean value. Use 'true'/'false'. Defaulting to '{DEFAULT_YOUTUBE_AUTOPLAY}'")
            except configparser.NoOptionError:
                warnings.append(f"[YouTube] autoplay not specified. Defaulting to '{DEFAULT_YOUTUBE_AUTOPLAY}'")
                
            try:
                autoclose = config.get('YouTube', 'autoclose')
                if not is_truthy_falsy(autoclose):
                    warnings.append(f"[YouTube] autoclose = '{autoclose}' is not a valid boolean value. Use 'true'/'false'. Defaulting to '{DEFAULT_YOUTUBE_AUTOCLOSE}'")
            except configparser.NoOptionError:
                warnings.append(f"[YouTube] autoclose not specified. Defaulting to '{DEFAULT_YOUTUBE_AUTOCLOSE}'")
    
            try:
                fullscreen = config.get('YouTube', 'fullscreen')
                if not is_truthy_falsy(fullscreen):
                    warnings.append(f"[YouTube] fullscreen = '{fullscreen}' is not a valid boolean value. Use 'true'/'false'. Defaulting to '{DEFAULT_YOUTUBE_FULLSCREEN}'")
            except configparser.NoOptionError:
                if WINDOWS_OS:
                    warnings.append(f"[YouTube] fullscreen not specified. Defaulting to '{DEFAULT_YOUTUBE_FULLSCREEN}'")

            try:
                shuffle = config.get('YouTube', 'shuffle')
                if not is_truthy_falsy(shuffle):
                    warnings.append(f"[YouTube] shuffle = '{shuffle}' is not a valid boolean value. Use 'true'/'false'. Defaulting to '{DEFAULT_YOUTUBE_SHUFFLE}'")
            except configparser.NoOptionError:
                warnings.append(f"[YouTube] shuffle not specified. Defaulting to '{DEFAULT_YOUTUBE_SHUFFLE}'")

            try:
                loop = config.get('YouTube', 'loop')
                if not is_truthy_falsy(loop):
                    warnings.append(f"[YouTube] loop = '{loop}' is not a valid boolean value. Use 'true'/'false'. Defaulting to '{DEFAULT_YOUTUBE_LOOP}'")
            except configparser.NoOptionError:
                warnings.append(f"[YouTube] loop not specified. Defaulting to '{DEFAULT_YOUTUBE_LOOP}'")

            try:
                cc = config.get('YouTube', 'cc')
                if not is_truthy_falsy(cc):
                    warnings.append(f"[YouTube] cc = '{cc}' is not a valid boolean value. Use 'true'/'false'. Defaulting to '{DEFAULT_YOUTUBE_CC}'")
            except configparser.NoOptionError:
                warnings.append(f"[YouTube] loop not specified. Defaulting to '{DEFAULT_YOUTUBE_CC}'")

            try:
                video_controls = config.get('YouTube', 'video_controls')
                if not is_truthy_falsy(video_controls):
                    warnings.append(f"[YouTube] video_controls = '{video_controls}' is not a valid boolean value. Use 'true'/'false'. Defaulting to '{DEFAULT_YOUTUBE_CONTROLS}'")
            except configparser.NoOptionError:
                warnings.append(f"[YouTube] video_controls not specified. Defaulting to '{DEFAULT_YOUTUBE_CONTROLS}'")

            try:
                keyboard = config.get('YouTube', 'keyboard')
                if not is_truthy_falsy(keyboard):
                    warnings.append(f"[YouTube] keyboard = '{keyboard}' is not a valid boolean value. Use 'true'/'false'. Defaulting to '{DEFAULT_YOUTUBE_KEYBOARD}'")
            except configparser.NoOptionError:
                warnings.append(f"[YouTube] keyboard not specified. Defaulting to '{DEFAULT_YOUTUBE_KEYBOARD}'")

            try:
                fsbutton = config.get('YouTube', 'fsbutton')
                if not is_truthy_falsy(fsbutton):
                    warnings.append(f"[YouTube] fsbutton = '{fsbutton}' is not a valid boolean value. Use 'true'/'false'. Defaulting to '{DEFAULT_YOUTUBE_FSBUTTON}'")
            except configparser.NoOptionError:
                warnings.append(f"[YouTube] fsbutton not specified. Defaulting to '{DEFAULT_YOUTUBE_FSBUTTON}'")

            try:
                annotations = config.get('YouTube', 'annotations')
                if not is_truthy_falsy(annotations):
                    warnings.append(f"[YouTube] annotations = '{annotations}' is not a valid boolean value. Use 'true'/'false'. Defaulting to '{DEFAULT_YOUTUBE_ANNOTATIONS}'")
            except configparser.NoOptionError:
                warnings.append(f"[YouTube] annotations not specified. Defaulting to '{DEFAULT_YOUTUBE_ANNOTATIONS}'")

            try:
                nocookie = config.get('YouTube', 'nocookie')
                if not is_truthy_falsy(nocookie):
                    warnings.append(f"[YouTube] nocookie = '{nocookie}' is not a valid boolean value. Use 'true'/'false'. Defaulting to '{DEFAULT_YOUTUBE_NOCOOKIE}'")
            except configparser.NoOptionError:
                warnings.append(f"[YouTube] nocookie not specified. Defaulting to '{DEFAULT_YOUTUBE_NOCOOKIE}'")

            try:
                language = config.get('YouTube', 'language').lower()
                if not is_valid_language_format(language):
                    warnings.append(f"[YouTube] Invalid language format: '{language}'. Expected format like 'en' or 'zh-tw'. Defaulting to system/YouTube language.")
            except configparser.NoOptionError:
                pass
            
            try:
                update_title = config.get('YouTube', 'update_title')
                if not is_truthy_falsy(update_title):
                    warnings.append(f"[YouTube] update_title = '{update_title}' is not a valid boolean value. Use 'true'/'false'. Defaulting to '{DEFAULT_YOUTUBE_UPDATE_TITLE}'")
            except configparser.NoOptionError:
                warnings.append(f"[YouTube] update_title not specified. Defaulting to '{DEFAULT_YOUTUBE_UPDATE_TITLE}'")

            service_override_settings('YouTube')

    except configparser.NoSectionError:
        warnings.append(f"Missing [YouTube] section in config.ini. Using default values: autoplay='{DEFAULT_YOUTUBE_AUTOPLAY}', loop='{DEFAULT_YOUTUBE_LOOP}', shuffle='{DEFAULT_YOUTUBE_SHUFFLE}', fullscreen='{DEFAULT_YOUTUBE_FULLSCREEN}', autoclose='{DEFAULT_YOUTUBE_AUTOCLOSE}', update_title='{DEFAULT_YOUTUBE_UPDATE_TITLE}'")

    # Check Twitch section
    try:
        if not config.has_section('Twitch'):
            warnings.append(f"Missing [Twitch] section in config.ini. Using default values: volume='{DEFAULT_TWITCH_VOLUME}', extensions='{DEFAULT_TWITCH_EXTENSIONS}', video_quality='{DEFAULT_TWITCH_QUALITY}'.")
        else:
            # Validate video_quality
            try:
                video_quality = config.get('Twitch', 'video_quality').strip()
                if not video_quality:
                    warnings.append(f"[Twitch] video_quality is empty. Using default of '{DEFAULT_TWITCH_QUALITY}' quality")
                else:
                    # Split and validate each quality in the list
                    qualities = [q.strip() for q in video_quality.split(',')]
                    for q in qualities:
                        if q.lower() not in ('source', 'auto'):
                            if not re.fullmatch(r'\d+p(60)?', q.lower()):
                                errors.append(
                                    f"[Twitch] Invalid quality '{q}' in video_quality. "
                                    "Must be 'source', 'auto', or resolution like '1080p60' or '720p'. "
                                    "For multiple qualities, use comma-separated values."
                                )
                                break  # Stop after first invalid quality
                    
            except configparser.NoOptionError:
                warnings.append(f"[Twitch] video_quality not specified. Using default of '{DEFAULT_TWITCH_QUALITY}' quality")
    
            # Validate volume
            try:
                volume = config.getint('Twitch', 'volume')
                if not (1 <= volume <= 100):
                    warnings.append(f"[Twitch] Invalid volume value '{volume}'. Must be between 1 and 100. Using default of '{DEFAULT_TWITCH_VOLUME}'")
            except configparser.NoOptionError:
                warnings.append(f"[Twitch] volume not specified. Defaulting to '{DEFAULT_TWITCH_VOLUME}'")
            except ValueError:
                warnings.append(f"[Twitch] volume must be a valid integer. Using default of '{DEFAULT_TWITCH_VOLUME}'")
    
            # Validate extensions
            try:
                extensions = config.get('Twitch', 'extensions')
                if not is_truthy_falsy(extensions):
                    warnings.append(f"[Twitch] extensions = '{extensions}' is not a valid boolean value. Use 'true'/'false'. Using default of '{DEFAULT_TWITCH_EXTENSIONS}'")
            except configparser.NoOptionError:
                warnings.append(f"[Twitch] extensions not specified. Defaulting to '{DEFAULT_TWITCH_EXTENSIONS}'")

            service_override_settings('Twitch')

            # Verify chat variables
            for key in ['chat_height', 'chat_width', 'chat_x_pos', 'chat_y_pos']:
                try:
                    value_str = config.get('Twitch', key)
                    if value_str:  # Only check if value exists
                        try:
                            int(value_str)  # Verify it's convertible to int
                        except ValueError:
                            errors.append(f"[Twitch] {key} must be a valid integer. Got '{value_str}'")
                except configparser.NoOptionError:
                    pass
    
            # Validate dark mode
            try:
                chat_dark_mode = config.get('Twitch', 'chat_dark_mode')
                if not is_truthy_falsy(chat_dark_mode):
                    warnings.append(f"[Twitch] chat_dark_mode = '{chat_dark_mode}' is not a valid boolean value. Use 'true'/'false'. Using default of '{DEFAULT_TWITCH_CHAT_DARK_MODE}'")
            except configparser.NoOptionError:
                pass

    except configparser.NoSectionError:
        warnings.append(f"Missing [Twitch] section in config.ini. Using default values: volume='{DEFAULT_TWITCH_VOLUME}', extensions='{DEFAULT_TWITCH_EXTENSIONS}', video_quality='{DEFAULT_TWITCH_QUALITY}'.")

    # Check Kick section
    try:
        if not config.has_section('Kick'):
            pass
        else:
            service_override_settings('Kick')
    except configparser.NoSectionError:
        pass

    return warnings, errors

def initialize_config(config_path):
    config = configparser.ConfigParser()
    if not os.path.exists(config_path):
      # print(f"Creating default config.ini at {config_path}...")
        try:
            with open(config_path, 'w') as f:
                f.write(DEFAULT_CONFIG)
            config.read_string(DEFAULT_CONFIG)
            print(f"Default config.ini file created at '{config_path}'.")
        except IOError as e:
            print(f"Error creating config file: {e}")
            sys.exit(1)
    else:
        try:
            config.read(config_path)
        except configparser.Error as e:
            print(f"Error reading config file: {e}")
            sys.exit(1)
    
    is_server = os.path.basename(sys.argv[0]).lower().startswith('streamledge_server')
    warnings, errors = validate_config(config)

    if warnings:
        print("\033[33mWARNINGS\033[0m found in config.ini:")
        for warning in warnings:
            print(f"\033[33m------->\033[0m {warning}")  # Yellow for warnings
    
    if errors:
        print("\033[91mERRORS\033[0m found in config.ini:")
        for error in errors:
            print(f"\033[91m------->\033[0m {error}")  # Bright red for errors

        if is_server:
            print("\nPlease fix the configuration errors in config.ini. Ideally, also only start the server with 'streamledge --start' instead of running it directly (unless you're testing stuff)")
            sys.exit(1)  

        response = input("\nWould you like to OVERWRITE your config.ini file with default configuration? (y/N): ").lower()
        if response == 'y':
            try:
                with open(config_path, 'w') as f:
                    f.write(DEFAULT_CONFIG)
                config.read_string(DEFAULT_CONFIG)
                print("\nDefault configuration restored.")
                sys.exit(0)
            except IOError as e:
                print(f"\nError writing config.ini file: {e}")
                sys.exit(1)
        else:
            print("\nPlease fix the configuration errors in config.ini.")
            sys.exit(1)
    
    # Calculate window dimensions based on video resolution (16:9 aspect ratio)
    display_area_height = config.getint('Browser', 'display_area_height', fallback=DEFAULT_DISPLAY_AREA_HEIGHT)
    width = round(display_area_height * 16 / 9)  # ROUND!
    height = display_area_height
    
    # Adjust titlebar_height
    try:
        titlebar_setting = config.get('Browser', 'titlebar_height')
        titlebar_height = int(titlebar_setting)
        if titlebar_height < 0:
            raise ValueError
    except (configparser.NoOptionError, ValueError):
        # Use system-detected titlebar height if missing or invalid
        titlebar_height = get_titlebar_height()
        config.set('Browser', 'titlebar_height', str(titlebar_height))
    
    # Add calculated dimensions to config
    config.set('Browser', 'width', str(width))
    config.set('Browser', 'height', str(height))
    
    # Check if positions need centering
    should_center_x = is_nullish(config, 'Browser', 'x_pos')
    should_center_y = is_nullish(config, 'Browser', 'y_pos')
    
    if should_center_x or should_center_y:
        # Get centered positions (only calculates what's needed - returns DEFAULT value if not should_center)
        x_pos, y_pos = get_window_position(
            height=height,
            width=width,
            center_x=should_center_x,
            center_y=should_center_y
        )
        
    # Update x and y positions
    if should_center_x:
        config.set('Browser', 'x_pos', str(x_pos))
        config.set('Browser', 'should_center_x_pos', 'true')
    
    if should_center_y:
        config.set('Browser', 'y_pos', str(y_pos))
        config.set('Browser', 'should_center_y_pos', 'true')

    # Set browser path
    config.set('Browser', 'browser_path', get_valid_default_web_browser())

    def set_config_bool(config, section, option, default=False):
        """Standardizes boolean config values with proper default handling"""
        # If option exists and has a value
        if not is_nullish(config, section, option):
            # Convert existing value to standardized true/false
            config.set(section, option, 'true' if is_true(config.get(section, option)) else 'false')
        # If option doesn't exist or is nullish
        else:
            # Set to default value
            config.set(section, option, 'true' if default else 'false')

    # user_data_dir - invalid values are errors in validate_config
    if is_nullish(config, 'Browser', 'user_data_dir'):
        config.set('Browser', 'user_data_dir', os.path.join(CONFIG_DIR, 'browser-user-data'))

    # Add true/false values
    set_config_bool(config, 'Twitch', 'muted', default=DEFAULT_MUTED)
    set_config_bool(config, 'Browser', 'title_suffix', default=DEFAULT_TITLE_SUFFIX)
    set_config_bool(config, 'YouTube', 'autoplay', default=DEFAULT_YOUTUBE_AUTOPLAY)
    set_config_bool(config, 'YouTube', 'loop', default=DEFAULT_YOUTUBE_LOOP)
    set_config_bool(config, 'YouTube', 'shuffle', default=DEFAULT_YOUTUBE_SHUFFLE)
    set_config_bool(config, 'YouTube', 'fullscreen', default=DEFAULT_YOUTUBE_FULLSCREEN)
    set_config_bool(config, 'YouTube', 'autoclose', default=DEFAULT_YOUTUBE_AUTOCLOSE)
    set_config_bool(config, 'Twitch', 'extensions', default=DEFAULT_TWITCH_EXTENSIONS)

    # Restore default YouTube language if user-specified value is not set/invalid
    try:
        language = config.get('YouTube', 'language').lower()
        if not is_valid_language_format(language):
            config.set('YouTube', 'language', DEFAULT_YOUTUBE_LANGUAGE)
    except configparser.NoOptionError:
        config.set('YouTube', 'language', DEFAULT_YOUTUBE_LANGUAGE)

    # Add Twitch volume if section is missing, empty or invalid
    vol_str = config.get('Twitch', 'volume', fallback='').strip()
    if not (vol_str.isdigit() and 1 <= int(vol_str) <= 100):
        config.set('Twitch', 'volume', str(DEFAULT_TWITCH_VOLUME))  # Set default if invalid

    # Add default Twitch video quality if section is missing or empty (invalid is an error)
    if is_nullish(config, 'Twitch', 'video_quality'):
        config.set('Twitch', 'video_quality', DEFAULT_TWITCH_QUALITY)

    chat_height = config.getint('Twitch', 'chat_height', fallback=DEFAULT_TWITCH_CHAT_HEIGHT)    
    chat_width = config.getint('Twitch', 'chat_width', fallback=DEFAULT_TWITCH_CHAT_WIDTH)
    config.set('Twitch', 'chat_height', str(chat_height))
    config.set('Twitch', 'chat_width', str(chat_width))

    # Decide if we should be trying to center Twitch chat x_pos and/or y_pos
    should_center_chat_x = is_nullish(config, 'Twitch', 'chat_x_pos')
    should_center_chat_y = is_nullish(config, 'Twitch', 'chat_y_pos')

    if should_center_chat_x or should_center_chat_y:
        # Get centered positions (only calculates what's needed - returns DEFAULT value if not should_center)
        chat_x_pos, chat_y_pos = get_window_position(
            height=chat_height,
            width=chat_width,
            default_x_pos=DEFAULT_TWITCH_CHAT_X_POS,
            default_y_pos=DEFAULT_TWITCH_CHAT_Y_POS,
            center_x=should_center_chat_x,
            center_y=should_center_chat_y
        )

    # Update x and y positions
    if should_center_chat_x:
        config.set('Twitch', 'chat_x_pos', str(chat_x_pos))
        config.set('Twitch', 'should_center_chat_x_pos', 'true')
    
    if should_center_chat_y:
        config.set('Twitch', 'chat_y_pos', str(chat_y_pos))
        config.set('Twitch', 'should_center_chat_y_pos', 'true')

    return config

def get_script_dir():
    if getattr(sys, 'frozen', False):  # Bundled executable
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

SCRIPT_DIR = get_script_dir()
CONFIG_DIR = user_config_dir(appname="streamledge", appauthor=False)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.ini")
os.makedirs(CONFIG_DIR, exist_ok=True)

class AppConfig:
    def __init__(self, config):
        """Initialize with existing ConfigParser object"""
        self._CONFIG = config  # Store the original config object
        
        # Server Settings
        self.PORT = self._get_int('Server', 'port')
        self.SERVER_SELF_DESTRUCT = self._get_bool('Server', 'self_destruct')

        # Browser Settings
        self.WINDOW_WIDTH = self._get_int('Browser', 'width')
        self.WINDOW_TITLEBAR_HEIGHT = self._get_int('Browser', 'titlebar_height')
        self.WINDOW_HEIGHT = self._get_int('Browser', 'height')
        self.WINDOW_X_POS = self._get_int('Browser', 'x_pos')
        self.WINDOW_Y_POS = self._get_int('Browser', 'y_pos')
        self.WINDOW_CENTER_X_POS = self._get_bool('Browser', 'should_center_x_pos')
        self.WINDOW_CENTER_Y_POS = self._get_bool('Browser', 'should_center_y_pos')
        self.BROWSER_PATH = self._get_clean_path('Browser', 'browser_path')
        self.USER_DATA_DIR = self._get_clean_path('Browser', 'user_data_dir')
        self.BROWSER_ARGS = self._get_list('Browser', 'arguments')
        self.MUTED = self._get_bool('Browser', 'muted')
        
        # YouTube Settings
        self.YOUTUBE_AUTOPLAY = self._get_bool('YouTube', 'autoplay')
        self.YOUTUBE_AUTOCLOSE = self._get_bool('YouTube', 'autoclose')
        self.YOUTUBE_FULLSCREEN = self._get_bool('YouTube', 'fullscreen')
        self.YOUTUBE_SHUFFLE = self._get_bool('YouTube', 'shuffle')
      # self.YOUTUBE_MUTED = self._get_bool('YouTube', 'muted')
        self.YOUTUBE_LOOP = self._get_bool('YouTube', 'loop')
        self.YOUTUBE_CC = self._get_bool('YouTube', 'cc')
        self.YOUTUBE_CONTROLS = self._get_bool('YouTube', 'video_controls')
        self.YOUTUBE_KEYBOARD = self._get_bool('YouTube', 'keyboard')
        self.YOUTUBE_FSBUTTON = self._get_bool('YouTube', 'fsbutton')
        self.YOUTUBE_ANNOTATIONS = self._get_bool('YouTube', 'annotations')
        self.YOUTUBE_LANGUAGE = self._get_str('YouTube', 'language').lower()
        self.YOUTUBE_UPDATE_TITLE = self._get_bool('YouTube', 'update_title')
        self.YOUTUBE_DOMAIN = "youtube-nocookie.com" if self._get_bool('YouTube', 'nocookie') else "youtube.com"
        
        # Twitch Settings
      # self.TWITCH_MUTED = self._get_bool('Twitch', 'muted')
        self.TWITCH_VOLUME = self._get_int('Twitch', 'volume')
        self.TWITCH_EXTENSIONS = self._get_bool('Twitch', 'extensions')
        self.TWITCH_QUALITY = self._get_str('Twitch', 'video_quality')
        self.TWITCH_CHAT_HEIGHT = self._get_int('Twitch', 'chat_height')
        self.TWITCH_CHAT_WIDTH = self._get_int('Twitch', 'chat_width')
        self.TWITCH_CHAT_X_POS = self._get_int('Twitch', 'chat_x_pos')
        self.TWITCH_CHAT_Y_POS = self._get_int('Twitch', 'chat_y_pos')
        self.TWITCH_CENTER_CHAT_X_POS = self._get_bool('Twitch', 'should_center_chat_x_pos')
        self.TWITCH_CENTER_CHAT_Y_POS = self._get_bool('Twitch', 'should_center_chat_y_pos')

        # Service-specific settings storage
        self._service_settings = {}
        self._load_service_settings(config)

    # Helper methods remain with lowercase names
    def _get_int(self, section: str, key: str, default: int = 0) -> int:
        try:
            return self._CONFIG.getint(section, key)
        except (configparser.NoOptionError, configparser.NoSectionError, ValueError):
            return default

    def _get_bool(self, section: str, key: str, default: bool = False) -> bool:
        val = self._get_str(section, key, str(default)).lower()
        return val in ('true', 'yes', '1', 'on')

    def _get_str(self, section: str, key: str, default: str = '') -> str:
        try:
            return self._CONFIG.get(section, key).strip()
        except (configparser.NoOptionError, configparser.NoSectionError):
            return default

    def _get_clean_path(self, section: str, key: str, default: str = '') -> str:
        path = self._get_str(section, key, default)
        return path.replace('"', '').strip()

    def _get_list(self, section: str, key: str, default: List[str] = None) -> List[str]:
        default = default or []
        try:
            value = self._CONFIG.get(section, key)
            if value.lower() in ('true', 'false'):  # Handle legacy boolean strings
                return [value]
            return value.replace('\n', ' ').strip().split()
        except (configparser.NoOptionError, configparser.NoSectionError):
            return default

    def _load_service_settings(self, config):
        """Preload all service-specific settings"""
        services = ['YouTube', 'Twitch', 'Kick']  # Add all services
        for service in services:
            self._service_settings[service] = {
                'display_area_height': config.getint(service, 'display_area_height', fallback=None),
                'x_pos': config.getint(service, 'x_pos', fallback=None),
                'y_pos': config.getint(service, 'y_pos', fallback=None),
                'muted': config.getboolean(service, 'muted', fallback=None)
                # Add other service-specific settings
            }
    
    def get_service_setting(self, service, setting):
        """
        Get service-specific setting with proper fallback
        Returns None if setting or service doesn't exist
        """
        service_settings = self._service_settings.get(service, {})
        return service_settings.get(setting)