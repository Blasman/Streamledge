# Streamledge

Streamledge is a command line utility to launch the live stream or the most recent VOD of a specified Twitch user in a **minimal** chromium based web browser (default is Edge) "app" window. It also supports YouTube Video ID's/URL's.

Streamledge loads a local flask web server (~30 MB of memory) in the background when first ran. This allows Streamledge to automatically modify the titlebar info of the web browser window to display the Twitch user's display name instead of the default "Twitch" title. Streamledge also sets the loading **position** and **size** of the web browser window to a user-defined setting.

## Installation

#### 1. Download Application
Download the latest Streamledge version from [Releases](https://github.com/Blasman/Streamledge/releases) and extract the files to a desired location.

#### 2. Register Application on Twitch
1. Navigate to [Twitch Developer Console - Register Your Application](https://dev.twitch.tv/console/apps/create)
2. Provide application details:
   - **Application Name**: `Streamledge` (or custom name)
   - **OAuth Redirect URL**: `http://localhost`
   - **Application Category**: Select "Other"
3. Click "Create" and copy these credentials for your `config.ini` file in the next step:
   - `Client ID` (public identifier)
   - `Client Secret` (keep this private)

#### 3. Configure Application
Edit `config.ini` in your Streamledge directory:

```ini
[Twitch]
client_id = your_client_id_here
client_secret = your_client_secret_here

[Server]
port = 5008

[Browser]
width = 960
height = 570
x_pos = 240
y_pos = 240
```

Keep in mind that for the `height` option an additional 30 pixels are added to factor in the titlebar of the web browser window and maintain a 16:9 "display space" ratio to fit the video. The default setting (570) loads a 540p sized window while still using source video quality for Twitch.

Streamledge creates it's own web browser user profile directory located in the Streamledge directory at `BrowserProfile`. You can follow the Twitch home link on a video and then log in to Twitch on your new profile so that your Twitch login info will be saved. Using a user profile just for Streamledge prevents weird window placement issues that can happen on initial window loading and keeps the video player as "clean" as possible.

Streamledge defaults to using Edge web browser on Windows. For other OS's (untested) or to use a different Chromium based web browser, add a `browser_path = ` line under the `[Browser]` section and specify the full path to your web browsers executable file.

## Usage

Manually pre-start background process for the Streamledge server:
```
streamledge.exe --start
```
Terminate background process for the Streamledge server:
```
streamledge.exe --stop
```
Play the Twitch live stream of a specified user:
```
streamledge.exe --live username
```
Play the most recent Twitch VOD of a specified user:
```
streamledge.exe --vod username
```
Play YouTube Video ID or URL:
```
streamledge.exe --yt 59H3_8oCqic
streamledge.exe --yt https://www.youtube.com/watch?v=59H3_8oCqic
```

The streamledge service will automatically load in the background if not already loaded when the `--live` or `--vod` or `--yt` options are ran. You can use the `--start` option beforehand to pre-load the flask server, otherwise the first load of a video will have an additional small delay to load the flask server first.

It's worth noting that all Twitch videos will start muted. I believe this is unavoidable due to embedding the video and site restrictions.

## Screenshots

![Screenshot of --live command](https://i.imgur.com/eghEncz.png)

![Screenshot of --vod command](https://i.imgur.com/NRlunn8.png)

![Screenshot of --yt command](https://i.imgur.com/vN94Gee.png)

## Chatty Integration

To use with [Chatty](https://github.com/chatty/chatty), first create the streamledge alias in Chatty's "Custom Commands." To do this, navigate to Main > Settings > Click on 'Commands' under the 'Other' tab on the left > Click the '+' symbol on the top right and paste the following with the proper path to your `streamledge.exe` file:

`_streamledge_ /proc exec "C:/path/to/streamledge/streamledge.exe"`

Use this alias for your streamledge commands in Chatty. To create a "Play Stream" and "Play VOD" option at the top of both the Streams and Channel Context Menu's, press the 'Edit' button on the "Streams Context Menu" option in the "Custom Commands" section of Chatty and paste the following:

```
Play Stream{0}=$(_streamledge_) --live $(1-)
Play VOD{1}=$(_streamledge_) --vod $(1-)
-{2}
```

This example will add "Play Stream" and "Play VOD" options at the top of the Streams and Channel context menu's.

![Screenshot of Chatty menu](https://i.imgur.com/V3Q7l3z.png)

For YouTube, you can create a `/yt` command to open YouTube ID's/URL's pasted in chat (by copy/pasting the ID/URL into the chat's edit box with the `/yt` command).
In the same "Other - Commands" menu where the streamledge alias was created, add an alias for YouTube as well:

`/yt $(_streamledge_) --yt $$1`

## Compiling Python Scripts

If you would prefer to compile the python scripts yourself, first install required packages with `pip install -r requirements.txt` and then run `build.bat` (for Windows OS) or `build.sh` (other OS - untested).
