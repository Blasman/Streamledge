; *** FreeTube Band-Aid Integration for Streamledge -- AutoHotkey v1.1 Script ***
; Click 'Copy Invidious Link' on YouTube video/playlist context menu in FreeTube to open video/playlist in Streamledge

#Persistent
#SingleInstance Force

PreviousClipboard := Clipboard ; Ignore current clipboard content at startup
SetTimer, CheckClipboard, 500 ; Check every 500ms
return

CheckClipboard:
    ; Only proceed if FreeTube.exe is the active window
    if !WinActive("ahk_exe FreeTube.exe")
        return

    ; Only proceed if the clipboard contains text and has changed
    if (Clipboard != PreviousClipboard) && (Clipboard != "")
    {
        PreviousClipboard := Clipboard ; Store current clipboard content
        
        ; Check if clipboard contains a YouTube URL and extract ID
        youtubeID := ExtractYouTubeID(Clipboard)
        if (youtubeID != "")
        {
            ExternalProgram := "C:\scripts\streamledge\streamledge.exe"
            Run, "%ExternalProgram%" "--yt" "%youtubeID%", , Hide
        }
    }
return

ExtractYouTubeID(Url) {
    if (InStr(Url, "redirect.invidious.io/watch?v=")) {
        idStart := InStr(Url, "v=") + 2
        youtubeID := SubStr(Url, idStart)
        if (ampPos := InStr(youtubeID, "&")) {
            youtubeID := SubStr(youtubeID, 1, ampPos - 1)
        }
        return youtubeID
    }

    if (InStr(Url, "redirect.invidious.io/playlist?list=")) {
        idStart := InStr(Url, "list=") + 5
        playlistID := SubStr(Url, idStart)
        if (ampPos := InStr(playlistID, "&")) {
            playlistID := SubStr(playlistID, 1, ampPos - 1)
        }
        return playlistID
    }

    return ""
}
