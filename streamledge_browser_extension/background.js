const PORT = 5008;

// Platform-specific paths to ignore
const platformIgnorePaths = {
  twitch: ["directory", "category", "settings", "subscriptions", "moderation", "p", "blog"],
  kick: ["videos", "categories", "popular", "trending", "settings", "video", "category"]
};

// Helper to check if URL should be ignored
function shouldIgnoreUrl(url, platform) {
  const pathParts = new URL(url).pathname.split('/').filter(Boolean);
  if (platform === 'twitch' && pathParts[0] === 'videos') return pathParts.length === 1;
  if (pathParts.length !== 1) return true;
  return platformIgnorePaths[platform].includes(pathParts[0].toLowerCase());
}

// Helper to open tab
function openTab(endpoint) {
  chrome.tabs.create({ url: `http://localhost:${PORT}/${endpoint}` });
}

// Helper to fetch Streamledge
function fetchStreamledge(endpoint) {
  fetch(`http://localhost:${PORT}/${endpoint}&runStreamledge=1`);
}

// Unified Twitch clip handler
function handleTwitchClip(info, url) {
  let clipId = null;

  // Embedded clip
  if (url.hostname === 'clips.twitch.tv' && url.pathname === '/embed') {
    clipId = url.searchParams.get('clip');
  }

  // Channel clip
  const pathParts = url.pathname.split('/').filter(Boolean);
  if (!clipId && pathParts.length >= 3 && pathParts[1] === 'clip') {
    clipId = pathParts[2];
  }

  if (clipId) {
    const endpoint = `clip?id=${clipId}`;
    info.menuItemId.endsWith('-newtab') ? openTab(endpoint) : fetchStreamledge(endpoint);
  }
}

// Context menu setup
chrome.runtime.onInstalled.addListener(() => {
  const menus = [
    // YouTube video (supports youtube.com and youtu.be)
    { id: "youtube-video", title: "Open Video in Streamledge", pattern: ["*://*.youtube.com/watch?v=*", "*://youtu.be/*"] },
    { id: "youtube-video-newtab", title: "Open Video in New Tab", pattern: ["*://*.youtube.com/watch?v=*", "*://youtu.be/*"] },

    // YouTube playlist (support watch?list= and short links with ?list=)
    { id: "youtube-playlist", title: "Open Playlist in Streamledge", pattern: ["*://*.youtube.com/watch?*list=*", "*://youtu.be/*"] },
    { id: "youtube-playlist-newtab", title: "Open Playlist in New Tab", pattern: ["*://*.youtube.com/watch?*list=*", "*://youtu.be/*"] },
    { id: "youtube-playlist-shuffled", title: "Shuffle Playlist in Streamledge", pattern: ["*://*.youtube.com/watch?*list=*", "*://youtu.be/*"] },
    { id: "youtube-playlist-shuffled-newtab", title: "Shuffle Playlist in New Tab", pattern: ["*://*.youtube.com/watch?*list=*", "*://youtu.be/*"] },

    // YouTube Shorts
    { id: "youtube-shorts", title: "Open Short in Streamledge", pattern: ["*://*.youtube.com/shorts/*"] },
    { id: "youtube-shorts-newtab", title: "Open Short in New Tab", pattern: ["*://*.youtube.com/shorts/*"] },

    // Twitch
    { id: "twitch-direct-vod", title: "Open Direct VOD in Streamledge", pattern: ["*://*.twitch.tv/videos/*"] },
    { id: "twitch-direct-vod-newtab", title: "Open Direct VOD in New Tab", pattern: ["*://*.twitch.tv/videos/*"] },
    { id: "twitch-channel", title: "Open Live Stream in Streamledge", pattern: ["*://*.twitch.tv/*"] },
    { id: "twitch-channel-newtab", title: "Open Live Stream in New Tab", pattern: ["*://*.twitch.tv/*"] },
    { id: "twitch-vod", title: "Open Recent VOD in Streamledge", pattern: ["*://*.twitch.tv/*"] },
    { id: "twitch-vod-newtab", title: "Open Recent VOD in New Tab", pattern: ["*://*.twitch.tv/*"] },
    { id: "twitch-chat", title: "Open Chat in Streamledge", pattern: ["*://*.twitch.tv/*"] },
    { id: "twitch-chat-newtab", title: "Open Chat in New Tab", pattern: ["*://*.twitch.tv/*"] },
    { id: "twitch-clip-channel", title: "Open Clip in Streamledge", pattern: ["*://*.twitch.tv/*/clip/*"] },
    { id: "twitch-clip-channel-newtab", title: "Open Clip in New Tab", pattern: ["*://*.twitch.tv/*/clip/*"] },
    { id: "twitch-clip-embed", title: "Open Clip in Streamledge", pattern: ["*://clips.twitch.tv/embed?clip=*"] },
    { id: "twitch-clip-embed-newtab", title: "Open Clip in New Tab", pattern: ["*://clips.twitch.tv/embed?clip=*"] },

    // Kick
    { id: "kick-channel", title: "Open Channel in Streamledge", pattern: ["*://*.kick.com/*"] },
    { id: "kick-channel-newtab", title: "Open Channel in New Tab", pattern: ["*://*.kick.com/*"] }
  ];

  menus.forEach(menu => {
    chrome.contextMenus.create({
      id: menu.id,
      title: menu.title,
      contexts: ["link"],
      targetUrlPatterns: Array.isArray(menu.pattern) ? menu.pattern : [menu.pattern]
    });
  });
});

// Click handler
chrome.contextMenus.onClicked.addListener((info) => {
  const url = new URL(info.linkUrl);
  const pathParts = url.pathname.split('/').filter(Boolean);
  let videoId = url.searchParams.get('v');
  let listId = url.searchParams.get('list');
  const hostname = url.hostname.toLowerCase();

  // Support youtu.be short links: video id is first path segment
  if (hostname === 'youtu.be' || hostname.endsWith('.youtu.be')) {
    if (pathParts.length >= 1) {
      // sometimes youtu.be/<id> or youtu.be/<id>?list=...
      videoId = pathParts[0];
    }
    // listId already parsed via searchParams if present
  }

  switch (info.menuItemId) {
    case "youtube-video":
      if (videoId) fetchStreamledge(`youtube?id=${videoId}`);
      break;
    case "youtube-video-newtab":
      if (videoId) openTab(`youtube?id=${videoId}`);
      break;
    case "youtube-playlist":
      if (listId) fetchStreamledge(`youtube?id=${listId}`);
      break;
    case "youtube-playlist-newtab":
      if (listId) openTab(`youtube?id=${listId}`);
      break;
    case "youtube-playlist-shuffled":
      if (listId) fetchStreamledge(`youtube?id=${listId}&shuffle=1`);
      break;
    case "youtube-playlist-shuffled-newtab":
      if (listId) openTab(`youtube?id=${listId}&shuffle=1`);
      break;
    case "youtube-shorts":
    case "youtube-shorts-newtab":
      if (pathParts[0] === "shorts" && pathParts[1]) {
        const shortsId = pathParts[1];
        const endpoint = `youtube?id=${shortsId}`;
        info.menuItemId.endsWith('-newtab') ? openTab(endpoint) : fetchStreamledge(endpoint);
      }
      break;

    case "twitch-direct-vod":
      fetchStreamledge(`twitch?contentType=vodid&vodid=${pathParts[1]}`);
      break;
    case "twitch-direct-vod-newtab":
      openTab(`twitch?contentType=vodid&vodid=${pathParts[1]}`);
      break;

    case "twitch-channel":
    case "twitch-channel-newtab":
    case "twitch-vod":
    case "twitch-vod-newtab":
    case "twitch-chat":
    case "twitch-chat-newtab":
      if (!shouldIgnoreUrl(info.linkUrl, 'twitch')) {
        const username = pathParts[0];
        const type = info.menuItemId.includes('vod') ? 'vod' :
                     info.menuItemId.includes('chat') ? 'chat' : '';
        const endpoint = `twitch?channel=${username}${type ? `&contentType=${type}` : ''}`;
        info.menuItemId.endsWith('-newtab') ? openTab(endpoint) : fetchStreamledge(endpoint);
      }
      break;

    case "twitch-clip-channel":
    case "twitch-clip-channel-newtab":
    case "twitch-clip-embed":
    case "twitch-clip-embed-newtab":
      handleTwitchClip(info, url);
      break;

    case "kick-channel":
    case "kick-channel-newtab":
      if (!shouldIgnoreUrl(info.linkUrl, 'kick')) {
        const kickChannel = pathParts[0];
        const endpoint = `kick?channel=${kickChannel}`;
        info.menuItemId.endsWith('-newtab') ? openTab(endpoint) : fetchStreamledge(endpoint);
      }
      break;
  }
});
