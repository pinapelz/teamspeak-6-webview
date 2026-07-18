import json
import time
from pathlib import Path
from urllib.parse import quote

import requests
from flask import Flask, Response, render_template_string, request, send_from_directory
from flask_cors import CORS

from config import BASE_DIR, CONFIG

app = Flask(__name__)
CORS(app)

ALLOWED_STATIC_EXTENSIONS = {
    ".css",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".svg",
    ".ico",
}


def safe_url(filename):
    return quote(str(filename or ""), safe="/")



def fetch_teamspeak_data(cfg):
    cache_file = Path(cfg["cache_file"])
    if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < cfg["cache_time"]:
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass

    base_url = f"https://{cfg['host']}:{cfg['port']}/{cfg['server_id']}"
    headers = {"x-api-key": cfg["api_key"]}

    try:
        channels_res = requests.get(f"{base_url}/channellist", headers=headers, timeout=2)
        clients_res = requests.get(f"{base_url}/clientlist?-groups", headers=headers, timeout=2)
        channels_json = channels_res.json()
        clients_json = clients_res.json()

        client_list = clients_json.get("body") or []

        afk_threshold = cfg.get("afk_status_max_clients")
        fetch_afk_status = afk_threshold is None or len(client_list) <= afk_threshold

        for client in client_list:
            clid = client.get("clid")
            nickname = client.get("client_nickname")
            if not fetch_afk_status:
                continue
            if clid and nickname != "serveradmin":
                client_info_res = requests.get(
                    f"{base_url}/clientinfo?clid={clid}",
                    headers=headers,
                    timeout=2,
                )
                body = client_info_res.json().get("body")
                if isinstance(body, list):
                    client_info = body[0] if body else {}
                else:
                    client_info = {}
                client["afk_text"] = client_info.get("client_away_message", "")
                client["is_afk"] = client_info.get("client_away") == "1"
                client["is_streaming"] = client_info.get("client_is_streaming") == "1"
                client["stream_text"] = client_info.get("client_stream_text", "")

    except requests.RequestException as e:
        print(f"RequestException: failed to fetch client info: {e}")
        return {"channels": [], "clients": []}
    except ValueError as e:
        print(f"ValueError: failed to parse client info: {e}")
        return {"channels": [], "clients": []}

    data = {
        "channels": channels_json.get("body") or [],
        "clients": client_list or [],
    }

    try:
        cache_file.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass

    return data


def same_id(left, right):
    return str(left or 0) == str(right or 0)


def sort_ts_channels(channels, pid=0):
    ordered = []
    by_order = {}

    for channel in channels:
        if same_id(channel.get("pid", 0), pid):
            by_order[str(channel.get("channel_order", 0))] = channel

    current_order = "0"
    max_iterations = len(channels) + 1
    iterations = 0

    while current_order in by_order and iterations < max_iterations:
        channel = by_order[current_order]
        ordered.append(channel)
        ordered.extend(sort_ts_channels(channels, channel.get("cid")))
        current_order = str(channel.get("cid"))
        iterations += 1

    return ordered


def build_context():
    start_time = time.perf_counter()
    ts_data = fetch_teamspeak_data(CONFIG["server"])
    api_ping = round((time.perf_counter() - start_time) * 1000)

    raw_channels = ts_data.get("channels") or []
    afk_count = None
    for channel in raw_channels:
        original_name = channel.get("channel_name", "")
        channel["is_spacer"] = "[Cspacer]" in original_name and "AFK" not in original_name
        # Channels with the keyword "AFK" count all connected clients as AFK regardless of status
        if "AFK" in original_name:
            afk_count = channel.get("total_clients", None)
        channel["channel_name"] = original_name.replace("[Cspacer]", "")
    raw_clients = ts_data.get("clients") or []
    is_online = bool(raw_channels)
    if afk_count is not None:
        afk_count = int(afk_count) - 1
    else:
        afk_count = 0

    channels = sort_ts_channels(raw_channels, 0)

    clients_by_channel = {}
    total_real_clients = 0

    if is_online:
        for client in raw_clients:
            if int(client.get("client_type") or 0) == 1:
                continue
            if client.get("is_afk"):
                afk_count += 1
            clients_by_channel.setdefault(str(client.get("cid")), []).append(client)
            total_real_clients += 1

    return {
        "config": CONFIG,
        "api_ping": api_ping,
        "channels": channels,
        "clients_by_channel": clients_by_channel,
        "is_online": is_online,
        "safe_url": safe_url,
        "total_real_clients": total_real_clients,
        "afk_count": afk_count,
    }


FRAGMENT_TEMPLATE = """
{% if is_online %}
    <div class="server-stats">
        <div class="stat-item">
            <span class="stat-label">Users Connected</span>
            <span class="stat-value">{{ total_real_clients }}</span>
        </div>
        {% if afk_count is not none %}
        <div class="stat-item">
            <span class="stat-label">AFK Users</span>
            <span class="stat-value">{{ afk_count }}</span>
        </div>
        {% endif %}
    </div>
    <div class="channel-list">
        {% for channel in channels %}
            {% set c_name = channel.get('channel_name', '') %}
            {% set cid = channel.get('cid')|string %}
            {% set channel_clients = clients_by_channel.get(cid, []) %}
            {% set bg_img = config.channel_banners.get(c_name, config.generic_images.get('background', '')) %}
            {% set icon_img = config.channel_icons.get(c_name, config.generic_images.get('icon', '')) %}

            {% if bg_img %}
                {% set bg_style = "background-image: linear-gradient(90deg, rgba(9, 18, 32, 0.96) 0%, rgba(9, 18, 32, 0.78) 45%, rgba(9, 18, 32, 0.94) 100%), url('" ~ safe_url(bg_img) ~ "');" %}
            {% else %}
                {% set bg_style = "" %}
            {% endif %}

            {% if not channel.is_spacer %}
            <article class="channel">
                <header class="channel-header" style="{{ bg_style }}">
                    <div class="channel-title-group">
                        {% if icon_img %}
                            <img src="{{ safe_url(icon_img) }}" class="channel-icon" alt="" aria-hidden="true">
                        {% endif %}
                        <h2>{{ c_name }}</h2>
                    </div>
                    {# Only show client count for non-spacer channels #}
                    <span class="channel-meta">
                        {{ channel_clients|length }}
                    </span>
                </header>

                {# Only show client list for non-spacer channels #}
                    <ul class="client-list">
                        {% for client in channel_clients %}
                            <li class="client">
                                {% set role_icon = namespace(path='') %}
                                {% for group_id in (client.get('client_servergroups', '')|string).split(',') %}
                                    {% if not role_icon.path and group_id in config.role_icons %}
                                        {% set role_icon.path = config.role_icons[group_id] %}
                                    {% endif %}
                                {% endfor %}

                                {% if role_icon.path %}
                                    <img src="{{ safe_url(role_icon.path) }}" class="role-icon" alt="Role">
                                {% else %}
                                    <span class="client-no-role-icon"></span>
                                {% endif %}
                                <span class="client-name">{{ client.get('client_nickname', '') }}</span>
                                {% if client.get('is_afk') %}
                                    <span class="client-afk">(AFK{% if client.get('afk_text') %}: {{ client.get('afk_text') }}{% endif %})</span>
                                {% endif %}
                                {% if client.get('is_streaming') %}
                                    <span class="client-stream">(Streaming{% if client.get('stream_text') %}: {{ client.get('stream_text') }}{% endif %})</span>
                                {% endif %}
                            </li>
                        {% endfor %}
                    </ul>
            </article>
            {% endif %}
        {% endfor %}
    </div>
{% else %}
    <div class="empty-server">Unable to reach the TeamSpeak server.</div>
{% endif %}
"""

PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{{ config.ui.subtitle }}">
    <title>{{ config.ui.title }}</title>
    <link rel="icon" type="image/png" href="logo.png">
    <link rel="stylesheet" href="index.css">
    <style>
        :root {
            --bg-color: {{ config.ui.background_color }};
            --panel-bg: {{ config.ui.panel_color }};
            --accent: {{ config.ui.accent_color }};
            --text-main: {{ config.ui.text_color }};
        }

    </style>
</head>
<body>


<main class="app-container">
    {% if is_online %}<div class="progress-bar" id="refresh-bar"></div>{% endif %}

    {% if config.ui.banner_url %}
        <img src="{{ safe_url(config.ui.banner_url) }}" alt="Header banner" class="banner">
    {% endif %}

    <div class="content-wrapper">
        <section id="ajax-container" aria-live="polite">
            {{ html_fragment|safe }}
        </section>

        {% if config.external_links %}
        <nav class="footer-links">
            {% for name, url in config.external_links.items() %}
                <a href="{{ url }}" target="_blank" rel="noopener">{{ name }}</a>
            {% endfor %}
        </nav>
        {% endif %}

        <header class="header">
            <h1>{{ config.ui.title }}</h1>
            <p>{{ config.ui.subtitle }}</p>
            {% if is_online %}
                <div class="status-badge status-online"><span class="pulse-dot"></span>SERVER ONLINE</div>
            {% else %}
                <div class="status-badge status-offline"><span class="pulse-dot"></span> SERVER OFFLINE</div>
            {% endif %}
        </header>

        <a href="ts3server://{{ config.server.ts_domain }}" class="btn-primary">{{ config.buttons.join }}</a>
        <p class="help-text">{{ config.buttons.download_text }} <a href="{{ config.buttons.download_url }}" target="_blank" rel="noopener">{{ config.buttons.download_link }}</a></p>


        <footer class="credits">
            {{ config.footer.text }} <a href="{{ config.footer.author_url }}" target="_blank" rel="noopener">{{ config.footer.author }}</a> — Refresh scan: <span id="timer-text">{{ config.server.cache_time }}</span>s
        </footer>
    </div>
</main>

<script>
    {% if is_online %}
    document.addEventListener("DOMContentLoaded", () => {
        let timeLeft = {{ config.server.cache_time|int }};
        const totalTime = {{ config.server.cache_time|int }};

        const progressBar = document.getElementById('refresh-bar');
        const timerText = document.getElementById('timer-text');
        const container = document.getElementById('ajax-container');

        function resetProgressBar() {
            progressBar.style.transition = 'none';
            progressBar.style.width = '100%';
            void progressBar.offsetWidth;
            progressBar.style.transition = `width ${totalTime}s linear`;
            progressBar.style.width = '0%';
        }

        resetProgressBar();

        setInterval(() => {
            timeLeft--;
            timerText.innerText = timeLeft;

            if (timeLeft <= 0) {
                container.style.opacity = '0.5';
                fetch(window.location.href.split('?')[0] + '?ajax=1', { cache: 'no-store', headers: {'X-Requested-With': 'XMLHttpRequest'} })
                    .then(r => {
                        if (!r.ok) throw new Error("HTTP error " + r.status);
                        return r.text();
                    })
                    .then(html => {
                        container.innerHTML = html;
                        container.style.opacity = '1';

                        timeLeft = totalTime;
                        timerText.innerText = timeLeft;

                        resetProgressBar();
                    })
                    .catch(err => {
                        console.error("Refresh failed:", err);
                        container.style.opacity = '1';
                        timeLeft = totalTime;
                        resetProgressBar();
                    });
            }
        }, 1000);
    });
    {% endif %}
</script>
</body>
</html>
"""


def render_fragment(context):
    return render_template_string(FRAGMENT_TEMPLATE, **context)


@app.route("/")
def index():
    context = build_context()
    html_fragment = render_fragment(context)

    if request.args.get("ajax") == "1":
        return Response(html_fragment, mimetype="text/html; charset=utf-8")

    return render_template_string(PAGE_TEMPLATE, html_fragment=html_fragment, **context)


@app.route("/<path:filename>")
def static_asset(filename):
    path = (BASE_DIR / filename).resolve()
    if (
        path.is_file()
        and BASE_DIR in path.parents
        and path.suffix.lower() in ALLOWED_STATIC_EXTENSIONS
    ):
        return send_from_directory(BASE_DIR, filename)
    return Response("Not found", status=404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
