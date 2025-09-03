<p align="center">
  <img src="assets/streamledge_logo.svg" alt="Streamledge" width="520">
</p>

# Streamledge

Streamledge is a command-line tool for playing YouTube and Twitch.tv videos.

Streamledge works by loading a lightweight (~30MB RAM) local flask web server in the background when first ran. This allows Streamledge to be ran with command line arguments that utilize the server to embed and play videos in a **minimal** [Chromium-based web browser](https://en.wikipedia.org/wiki/Chromium_(web_browser)#Browsers_based_on_Chromium) `--app` window.


# Usage Examples

### YouTube

Play the first YouTube search result for a **video**:

`sl --yt ava max american`

![Streamledge YouTube Screenshot](https://i.imgur.com/4eqH24I.png)

Play the first YouTube search result for a **playlist**:

`sl --ytpl dua lipa music videos`

![Streamledge YouTube Screenshot](https://i.imgur.com/doQCPv4.png)

Play YouTube video by ID and override `config.ini` settings to force autoplay, fullscreen, and autoclose (note: `--fullscreen` is Windows OS only):

`sl --yt dQw4w9WgXcQ --autoplay --fullscreen --autoclose`

Play YouTube video by URL and override `config.ini` settings to NOT autoplay and NOT run fullscreen:

`sl --yt "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=RDdQw4w9WgXcQ&start_radio=1" --autoplay 0 --fullscreen 0`

Shuffle and play a YouTube playlist:

`sl --ytpl dua lipa music videos --shuffle`

### Twitch.tv

Play a Twitch stream:

`sl --live hasanabi`

![Streamledge Twitch Screenshot](https://i.imgur.com/oPf1nEq.png)

Play the most recent VOD (including the VOD for an active live stream) for a Twitch channel:

`sl --vod hasanabi`

![Streamledge Twitch Screenshot](https://i.imgur.com/hBbpVbK.png)

Open the chat for a Twitch channel:

`sl --chat extraemily`

![Streamledge Twitch Screenshot](https://i.imgur.com/LzzIfsB.png)

Play Twitch stream in a 360p sized window at 360p quality and 1% volume:

`sl --live hasanabi --height 360 --quality 360p --volume 1`


# Installation

### 🪟 Windows Installation:

Open a command prompt and run:

```
py -m pip install --upgrade pip
py -m pip install streamledge
```

You can begin using Streamledge with the `sl` or `streamledge` command.

If `py` is not a valid command than you may be using the Windows Store version of Python (or no Python at all). It is recommended to use the [official Python release](https://www.python.org/downloads/windows/).

Included [here on this repo](Windows_Helper_Files/) are several simple `.bat` files for your double clicking conveinience.

### 🐧🍎 Linux/MacOS Installation:

Note: Streamledge has not been tested on MacOS.

Open a terminal and run:
```
python3 -m pip install --upgrade pip
python3 -m pip install streamledge
```

As long as Chrome or Chromium is installed in a default location, you should be able to begin using Streamledge with the `sl` or `streamledge` command.

## Recommended -> Configure Application

Run in terminal / command prompt:

`sl --appdata`

This will open the appdata directory for Streamledge in your systems file explorer so you may edit your `config.ini` file. Streamledge also stores its server log files and *default* web browser user data directory in this folder.

If Streamledge cannot find a default web browser, you will need to specify a path to one in `config.ini`.

With the exception of the server port, you do **not** need to restart the server for changes to take effect.

**Default config.ini file:**
```ini
[Server]

# Network port for the local Streamledge flask web server background service. The default of '5008' should be fine.
port = 5008

# Have the 'streamledge_server' process automatically terminate itself after serving content.
# Set to true/false
self_destruct = False

[Browser]

# Display area HEIGHT of the web browser window.
# Override with --height [num]
display_area_height = 540

# For Windows OS, Streamledge attempts to auto-detect windows titlebar_height which is required info to draw a properly sized browser window.
# For Linux OS, this info does not appear to be required, therefor '0' is the default non-Windows OS value.
# If you see any solid black color around the borders of the display area, then you may want to adjust your titlebar_height accordingly.
# To adjust or correctly set the height in pixels of your windows titlebars, uncomment the line below and set value.
# titlebar_height = 0

# For Windows OS and Linux OS, Streamledge attempts to position the web browser window in the middle and closer to the top of your display.
# For Mac OS or to manually set either of the X and/or Y position(s), uncomment the x_pos and/or y_pos lines below and set desired value(s).
# Override with --x [num]  and/or  --y [num]
# x_pos = 480
# y_pos = 135

# Streamledge searches your system for a suitable default chromium based web browser in order of preference:  MS Edge > Chrome > Chromium
# Optionally specify path to compatible chromium based web browser executable file by uncommenting the 'browser_path = ' line below.
# Override with --browser-path [path]
# browser_path = C:\Program Files\Google\Chrome\Application\chrome.exe

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
muted = False

# Optionally add service name suffix to window title in the form of ' - ServiceName'. eg: false == "UserName"  vs  true == "UserName - Twitch"
title_suffix = False

[YouTube]

# Automatically begin playback for videos/playlists.
# Set to true/false
# Override with --autoplay [0|1]
autoplay = True

# Automatically close the window when playback ends.
# Set to true/false
# Override with --autoclose [0|1]
autoclose = True

# WINDOWS OS ONLY. Automatically switch to fullscreen mode when playback begins. This is a bit of a gimmick.
# This simulates a double click on the video upon video playback and then moves/hides the mouse cursor back to its original position.
# Set to true/false
# Override with --fullscreen [0|1]
fullscreen = False

# Shuffle the *entire* playlist and return up to 200 results (200 is the limit for all embedded playlists).
# Set to true/false
# Override with --shuffle [0|1]
shuffle = False

# Enable continuous playback looping.
# Set to true/false
# Override with --loop [0|1]
loop = False

# Enable closed captioning on by default.
# Set to true/false
# Override with --cc [0|1]
cc = False

# Enable/disable video controls.
# Set to true/false
# Override with --video-controls [0|1]
video_controls = True

# Enable/disable keyboard controls.
# Set to true/false
# Overrise with --keyboard [0|1]
keyboard = True

# Enable/disable fullscreen button on GUI. Disabling the button also disables the ability to fullscreen.
# Set to true/false
# Override with --fsbutton [0|1]
fsbutton = True

# Enable/disable video annotations. Effectiveness is questionable. 'nocookie' option below has this forcibly disabled.
# Set to true/false
annotations = False

# Optionally play videos/playlists with 'youtube-nocookie.com' instead of 'youtube.com'.
# Set to true/false
nocookie = True

# Optionally set ISO 639-1 two-letter language code for YouTube GUI and preferred closed caption language.
# Reference: https://www.loc.gov/standards/iso639-2/php/code_list.php
# language = 

# Playlists only: Update the window titlebar with the name of the currently playing video.
# When 'true': Begin playback with the name of the playlist in the window titlebar until progressing to the next video.
# When 'false': Keeps the playlist name in the window titlebar at all times.
update_title = True

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
video_quality = source

# Set default volume percentage (1-100).
# Override with --volume [1-100]
volume = 100

# Enable Twitch extensions on the video overlay.
# Set to true/false
# Override with --extensions [0|1]
extensions = True

# Optionally override global [Browser] settings.
# display_area_height = 
# x_pos = 
# y_pos = 
# muted = 

# Optionally set size, loading position, and light/dark mode for --chat arg to open Twitch chat. (x and y will center if not set)
# Default settings will force the chat window to the right of the screen and utilize all screen space from top to bottom.
chat_height = 99999
chat_width = 600
chat_x_pos = 99999
chat_y_pos = 0
chat_dark_mode = True

[Kick]

# Optionally override global [Browser] settings.
# display_area_height = 
# x_pos = 
# y_pos = 
# muted = 
```


# Usage / Command Line Arguments

General command line arguments for `streamledge`:

`--help` or `--h` :: Show the following Streamledge help message and version number:
```
usage: sl [-h] [--start | --stop] [--config PATH] [--height HEIGHT] [--x X_POS] [--y Y_POS]
          [--browser-path PATH] [--data-dir DIR] [--muted [0|1]] [--url-only]
          [--yt VIDEO_ID(s)/URL(s)/QUERY [VIDEO_ID(s)/URL(s)/QUERY ...] |
          --ytpl PLAYLIST_ID/URL/QUERY [PLAYLIST_ID/URL/QUERY ...] | --ytsearch QUERY [QUERY ...] |
          --ytplsearch QUERY [QUERY ...] | --ytmix VIDEO_ID/URL/QUERY [VIDEO_ID/URL/QUERY ...]]
          [--autoplay [0|1]] [--autoclose [0|1]] [--fullscreen [0|1]] [--shuffle [0|1]]
          [--loop [0|1]] [--cc [0|1]] [--video-controls [0|1]] [--keyboard [0|1]]
          [--fsbutton [0|1]] [--vidstart TIME] [--plstart NUM]
          [--live CHANNEL/URL [CHANNEL/URL ...] | --vod CHANNEL[:N]/URL [CHANNEL[:N]/URL ...] |
          --vodid VOD ID/URL [VOD ID/URL ...] | --clip CLIP ID/URL [CLIP ID/URL ...] |
          --chat CHANNEL/URL [CHANNEL/URL ...]] [--volume [1-100]] [--extensions [0|1]]
          [--quality QUALITY] [--vodstart TIME] [--kick CHANNEL/URL [CHANNEL/URL ...] |
          --kickvod CHANNEL/URL [CHANNEL/URL ...]] [--browse [URL] | --appdata]

Streamledge v0.1.0

options:
  -h, --help            show this help message and exit
  --start               Start streamledge_server background process (NOT STRICTLY REQUIRED -
                        happens automatically if needed)
  --stop                Close streamledge_server background process

Player/Browser options:
  --config PATH         Path to alternate config file (either full path or filename in current
                        directory)
  --height, --size HEIGHT
                        Set display area height of web browser window
  --x X_POS             Set X position of browser window
  --y Y_POS             Set Y position of browser window
  --browser-path PATH   Full path to Chromium-based browser executable
  --data-dir DIR        Base dir for generated user data directory
  --muted [0|1]         Begin playback muted
  --url-only            Only display generated URL. Do not run Streamledge

YouTube.com options:
  --yt VIDEO_ID(s)/URL(s)/QUERY [VIDEO_ID(s)/URL(s)/QUERY ...]
                        Play YouTube video ID(s)/URL(s)/first search query result
  --ytpl PLAYLIST_ID/URL/QUERY [PLAYLIST_ID/URL/QUERY ...]
                        Play YouTube playlist ID/URL/first search query result
  --ytsearch QUERY [QUERY ...]
                        Search for videos and choose from the top 10 results
  --ytplsearch QUERY [QUERY ...]
                        Search for playlists and choose from the top 10 results
  --ytmix VIDEO_ID/URL/QUERY [VIDEO_ID/URL/QUERY ...]
                        Play YouTube generated Mix/Radio playlist from video
  --autoplay [0|1]      *OPTIONAL* Begin playback automaticaly
  --autoclose [0|1]     *OPTIONAL* Close window automatically when playback ends
  --fullscreen, --fs [0|1]
                        *OPTIONAL* Fullscreen video (auto mouse clicks window)
  --shuffle [0|1]       *OPTIONAL* Shuffle playlist order
  --loop [0|1]          *OPTIONAL* Toggle continuous playback looping
  --cc [0|1]            *OPTIONAL* Toggle closed captions on by default
  --video-controls [0|1]
                        *OPTIONAL* Toggle video controls
  --keyboard [0|1]      *OPTIONAL* Toggle keyboard controls
  --fsbutton [0|1]      *OPTIONAL* Toggle fullscreen button on GUI
  --vidstart TIME       *OPTIONAL* Begin video playback at timestamp like '120' for seconds or
                        '1h2m3s' (automatically detected if in URL)
  --plstart NUM         *OPTIONAL* Begin/create playlist from the NUM video of playlist

Twitch.tv options:
  --live, --twitch CHANNEL/URL [CHANNEL/URL ...]
                        Play live stream of channel name(s)
  --vod CHANNEL[:N]/URL [CHANNEL[:N]/URL ...]
                        Play most recent VOD of channel name(s). Add :N for Nth most recent (e.g.
                        username:2 for 2nd most recent)
  --vodid VOD ID/URL [VOD ID/URL ...]
                        Play Twitch VOD for ID(s)/URL(s)
  --clip CLIP ID/URL [CLIP ID/URL ...]
                        Play Twitch clips for ID(s)/URL(s)
  --chat CHANNEL/URL [CHANNEL/URL ...]
                        Open chat of channel names(s)
  --volume [1-100]      *OPTIONAL* Volume level (1-100)
  --extensions [0|1]    *OPTIONAL* Enable Twitch extensions on video
  --quality QUALITY     *OPTIONAL* Preferred video qualitie(s) (comma-separated list). Use
                        "source", "auto", or any resolution like "720p" or "1080p60"
  --vodstart TIME       *OPTIONAL* Begin VOD playback at timestamp like '1h2m3s' (automatically
                        detected if in URL)

Kick.com options:
  --kick CHANNEL/URL [CHANNEL/URL ...]
                        Play live stream of channel name(s)
  --kickvod CHANNEL/URL [CHANNEL/URL ...]
                        Play most recent VOD of channel name(s)

Misc options:
  --browse [URL]        Open browser normally (with optional URL). Install extensions, log in to
                        Twitch, etc.
  --appdata             Open Streamledge appdata directory in file explorer
```

`--start` :: Manually pre-start background process for the streamledge_server. This is not strictly required as the first usage of Streamledge to play a video will do this automatically at the cost of a very minor delay. If you would prefer to run the server in it's own terminal, you may run the `streamledge_server` command directly instead. Either way, server activity is logged to `streamledge_server.log` file.

`--stop` :: Terminate the active streamledge_server process.

`--url-only` :: Only display generated URL (for the local flask server). Do not launch browser.

### Optional config.ini Override Args

`--muted` :: Begin playback muted.

`--config PATH` :: Set path to custom config file. Note: if server is already active, just make sure that the Server 'port' is the same as the running server.

`--height HEIGHT` :: Set display area height of web browser window.

`--x X_POS` :: Set X position of browser window.

`--y Y_POS` :: Set Y position of browser window.

`--browser-path PATH` :: Full path to Chromium-based web browser executable.

`--data-dir DIR` :: Base dir for generated user data directory.


## YouTube.com
A nice side-effect of embedding YouTube videos with Streamledge is that this appears to remove all advertisements. A limitation of embedding is that age-restricted videos will not play.

`--yt` :: Play **Video** from specified video ID, URL, or search query. Specifying more than one video ID/URL will create a playlist.  **Examples:**
```
sl --yt 59H3_8oCqic
sl --yt https://www.youtube.com/watch?v=59H3_8oCqic
# Ideally use quotations for search queries, however, simple search queries will work without them:
sl --yt rick astley never gonna give
sl --yt "ava max my head & my heart"
sl --yt "https://www.youtube.com/watch?v=cTr-aGK-LpA&list=PLgtFJ5i1fDDdnkmR1ltQ0rwWebUMGM0ho"
# Use multiple video IDs/URLs to generate a playlist to play:
sl --yt https://www.youtube.com/watch?v=59H3_8oCqic https://www.youtube.com/watch?v=EOj4gOFn5QA https://www.youtube.com/watch?v=ijS_orLb6VU
```
`--ytpl` :: Play **Playlist** from specified playlist ID, URL, or search query. The first 200 videos (a limitation of embedding) are returned. You may combine with `--plstart` to work around this limitation. **Examples:**
```
sl --ytpl PLgtFJ5i1fDDdnkmR1ltQ0rwWebUMGM0ho
sl --ytpl "https://www.youtube.com/watch?v=cTr-aGK-LpA&list=PLgtFJ5i1fDDdnkmR1ltQ0rwWebUMGM0ho"
sl --ytpl 90s alternative rock
sl --ytpl "metallica black album"
sl --ytpl newest taylor swift album
```
`--ytmix` :: Play a YouTube **Mix/Radio** based off of specified video ID, URL, or search query. Note that this does not always return the original video, but always seems to return 49 videos.

`--ytsearch` :: Searches YouTube and returns the top 10 search results for videos and lets you choose from them.

`--ytplsearch` :: Same as above but for playlists.

### Optional YouTube Args

You may override any config.ini settings with these optional args.

#### Boolean YouTube Args

For 'True' you may use either `--arg 1` or `--arg`.
For 'False' you must use `--arg 0`.

`--autoplay` :: Begins playback automatically without user interaction.

`--autoclose` :: Closes video/playlist automatically when playback ends.

`--fullscreen` :: Windows OS only: Upon playback, automatically double clicks the window and moves the mouse cursor back to its original position.

`--shuffle` :: Shuffle the *entire* playlist and return up to 200 random videos.

`--loop` :: Continuous playback looping of videos/playlist.

`--cc` :: Closed captions on by default.

`--video-controls` :: Video controls for video/playlist.

`--keyboard` :: Keyboard controls for video/playlist.

`--fsbutton` :: Display fullscreen button. When disabled, also disables the option to fullscreen the video.

#### Other YouTube Args

`--vidstart TIME` :: Begin video playback at timestamp like '120' for seconds or '1h2m3s'. Start time is automatically detected if included in URL.

`--plstart NUM` :: Start/create playlist from the NUM video of specified/searched playlist.


## Twitch.tv
`--live` or `--twitch` :: Play the live stream of specified channel(s). **Examples:**
```
sl --live hasanabi
sl --live https://twitch.tv/hasanabi
```
`--vod` :: Play the most recent VOD of specified channel(s) (returns the VOD for the current live stream if auto-publish VOD is enabled by streamer). Use with optional :N parameter to play most recent Nth VOD. **Examples:**
```
# Play most recent VOD:
sl --vod extraemily
sl --vod https://twitch.tv/extraemily
# Play the second most recent VOD:
sl --vod extraemily:2
```
`--vodid` :: Play a specific VOD. **Examples:**
```
sl --vodid 2520137284
sl --vodid "https://www.twitch.tv/videos/2520137284?filter=archives&sort=time"
```
`--clip` :: Play a specific clip. **Examples:**
```
sl --clip MuddyPluckyNarwhalNotLikeThis-k5tg2-VPtLNDQv0_
sl --clip https://www.twitch.tv/extraemily/clip/MuddyPluckyNarwhalNotLikeThis-k5tg2-VPtLNDQv0_
sl --clip "https://clips.twitch.tv/embed?clip=MuddyPluckyNarwhalNotLikeThis-k5tg2-VPtLNDQv0_&parent=localhost"
```
`--chat` :: Opens chat for specified channel(s).

### Optional Twitch Args

#### Boolean Twitch Args

For 'True' you may use either `--arg 1` or `--arg`.
For 'False' you must use `--arg 0`.

`--extensions` :: Enable Twitch extensions on video overlay.

#### Other Twitch Args

`--volume [1-100]` :: Volume level from 1 to 100.

`--quality` :: Override config.ini setting for Twitch video_quality. **Examples:**
```
sl --live jinnytty --quality 720p60
sl --live jinnytty --quality 1080p
sl --live jinnytty --quality 1080p60
sl --live jinnytty --quality 720p,1080p,720p60
sl --live jinnytty --quality source
sl --vod jinnytty --quality auto
sl --vodid 2520137284 --quality source
```

`--vodstart` :: Begin VOD playback at timestamp like '1h2m3s'. Start time is automatically detected if included in URL.

## Kick.com
`--kick` :: Play the live stream of a specified user. **Examples:**
```
sl --kick rick92647
sl --kick https://kick.com/rick92647
```
`--kickvod` :: Play the most recent VOD of a specified user. **NOTICE**: this command will load the normal Kick webpage for the most recent VOD as embedding VOD's does not seem to be a Kick feature at the moment. **Examples:**
```
sl --kickvod rick92647
sl --kickvod https://kick.com/rick92647
```


## Misc
`--browse [URL]` :: Open web browser normally (with optional URL). This is to allow installing extensions, logging into Twitch, etc.

`--appdata` :: Open the appdata directory for Streamledge in your systems file explorer. You can find your `config.ini` file here.


# Web Browser Extension

Streamledge includes a web browser extension for chromium based web browsers that currently allows you to right click YouTube, Twitch, and Kick links to either open in Streamledge or open in a new tab.

You will obviously need to have the `streamledge_server` process running (by using `--start` or by playing a video with Streamledge first) for the menu options to function.

Until the extension is available via the Chrome/Edge web stores, you will need to enable developer mode in your browser and load unpacked extension from the [streamledge_browser_extension](/streamledge_browser_extension) folder. Slow one minute tutorial here: https://www.youtube.com/watch?v=AnvFyHUQw9M&t=5s

YouTube screenshot of Streamledge context menu in Chrome:

![Streamledge Browser_Extension Screenshot_01](https://i.imgur.com/k2dRUcL.png)

Twitch screenshot of Streamledge context menu in Chrome:

![Streamledge Browser_Extension Screenshot_02](https://i.imgur.com/z0m9hdO.png)


# Chatty Integration

To use with [Chatty](https://github.com/chatty/chatty), first create the streamledge alias in Chatty's "Custom Commands." To do this, navigate to Main > Settings > Click on 'Commands' under the 'Other' tab on the left > Click the '+' symbol on the top right and paste the following:

`_streamledge_ /proc exec streamledge`

You may use `/procEcho` instead of `/proc` if you would like to display Streamledge's output in Chatty (ie `SERVING URL:`).

Use this alias for your streamledge commands in Chatty. To create a "Play Stream" and "Play VOD" option at the top of both the Streams and Channel Context Menu's, press the 'Edit' button on the "Streams Context Menu" option in the "Custom Commands" section of Chatty and paste the following:

```
Play Stream{0}=$(_streamledge_) --live $(1-)
Play VOD{1}=$(_streamledge_) --vod $(1-)
-{2}
```

This example will add "Play Stream" and "Play VOD" options at the top of the Streams and Channel context menu's.

![Screenshot of Chatty menu](https://i.imgur.com/V3Q7l3z.png)

You can get creative by using command line arguments to create various menu options (ie "Play Stream Muted", etc). This example will add "quality options" for live streams:

```
Play Stream{0}=$(_streamledge_) --live $(1-)
Play VOD{1}=$(_streamledge_) --vod $(1-)
@Play Stream Options{2}
.source=$(_streamledge_) --live $(1-) --quality source
.auto=$(_streamledge_) --live $(1-) --quality auto
.1080p60=$(_streamledge_) --live $(1-) --quality 1080p60
.1080p=$(_streamledge_) --live $(1-) --quality 1080p
.720p60=$(_streamledge_) --live $(1-) --quality 720p60
.720p=$(_streamledge_) --live $(1-) --quality 720p
.480p=$(_streamledge_) --live $(1-) --quality 480p
.360p=$(_streamledge_) --live $(1-) --quality 360p
.160p=$(_streamledge_) --live $(1-) --quality 160p
-{3}
```

![Screenshot of Chatty menu](https://i.imgur.com/D128I3U.png)

For YouTube or Kick.com, you can create aliases to launch Streamledge. For example, you can create a `/yt`, `/kick`, etc alias to use in the editbox that will open Streamledge with provided arguments as if you were running it from the command line.

In the same "Other - Commands" menu where the streamledge alias was created, you may create these aliases:

```
/yt $(_streamledge_) --yt "$$1-"
/kick $(_streamledge_) --kick "$$1-"
```
Usage example: `/yt rick roll`


# FreeTube "Integration" (Windows OS)

Included on this repository is [a basic AutoHotkey (v1.1) script](Windows_Helper_Files/FreeTube-to-Streamledge.ahk) that when used with [FreeTube](https://github.com/FreeTubeApp/FreeTube) it will effectively turn the "Copy Invidious Link" context menu item into a Streamledge launcher for the linked video/playlist.
