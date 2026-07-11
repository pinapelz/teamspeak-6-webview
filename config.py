"""TeamSpeak Web Explorer configuration."""

from pathlib import Path
from dotenv import load_dotenv
import os
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

CONFIG = {
    # Server connection settings
    "server": {
        "host": os.environ.get("TS_HOST", ""),  # Server IP or hostname, e.g. 192.168.1.50
        "port": os.environ.get("TS_WEBQUERY_PORT", "8443"),  # HTTP WebQuery port (TS6)
        "api_key": os.environ.get("TS_API_KEY", ""),
        "server_id": os.environ.get("TS_SERVER_ID", "1"),
        "ts_domain": os.environ.get("TS_HOST", ""),  # Used by the connect button
        "cache_time": 30,  # Refresh interval in seconds (anti-spam)
        "cache_file": BASE_DIR / "cache.json",
    },

    # Main design and copy
    "ui": {
        "title": "",
        "subtitle": "",
        "background_color": "#07111f",  # Main background color
        "panel_color": "#101b2d",  # Main panel and channel block color
        "accent_color": "#2589ff",  # Buttons, highlights, and refresh timer
        "text_color": "#e8f2ff",
        "banner_url": "banner.jpg",  # Leave empty ('') to hide the header banner
        "enable_stars": True,  # Set to True to enable a subtle animated space background
    },

    # Interface buttons and links
    "buttons": {
        "join": "Connect to TeamSpeak",
        "download_text": "Teamspeak is not installed yet?",
        "download_link": "Download Teamspeak",
        "download_url": "https://www.teamspeak.com/en/downloads/",  # Official download link
    },

    # Useful links. Add or remove as many rows as you want.
    "external_links": {
    },

    # Footer
    "footer": {
        "text": "another moekyun service",
        "author": "",
        "author_url": "",
    },

    # Channel customization. Exact channel name => image filename.
    "channel_banners": {
        "INFORMATION": "info.png",
        "GAME SERVERS": "game.jpeg",
        "General": "general.jpg",
        "CRASHING OUT": "crash.png",
        "Wonhee HQ": "illit.jpg",
    },

    "channel_icons": {
        # "Lobby": "lobby_icon.png",
        # "General": "general_icon.png",
    },

    "generic_images": {
        "background": "",  # Default image applied to unknown channels
        "icon": "",  # Default icon applied to unknown channels
    },

    # Server groups / roles: 'GROUP_ID' => 'Image'
    "role_icons": {
        # "6": "admin.png",
        # "9": "vip.png",
    },
}
