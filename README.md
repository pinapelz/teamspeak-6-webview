# Teamspeak 6 Web Server Status
A simple webview of your Teamspeak 6 Server. This is a Python re-write of [ts6-web-explorer](https://github.com/Guraz/ts6-web-explorer) along with a visual overhaul 

<img width="852" height="906" alt="image" src="https://github.com/user-attachments/assets/00cf9ea7-cfad-4633-8d3b-7a66039fb87b" />

# Notes
```
uv sync
uv run app.py
```
- Rename `.env.template` to `.env` and fill in the parameters as required
- Spacer channels are hidden
- Channels with the text `AFK` are shown, the number of users in this channel is used as the AFK users indicator
- Edit and configure `config.py` for all other non-essential settings
