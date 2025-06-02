# 🌊 HubiWave

**HubiWave** is a self-hosted web interface to orchestrate SSH commands, remote scripts, and scheduled jobs across multiple Linux machines.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Flask](https://img.shields.io/badge/Built%20with-Flask-orange)

---

## 🚀 Features

- ⚡ Run **SSH commands** instantly across multiple machines
- 📂 Upload and execute **shell/Python scripts** remotely
- 🕒 Create advanced **recurring jobs** with cycles, spacing, and scheduling
- 🗓️ Visualize all jobs in a **calendar interface** (FullCalendar)
- 🧠 No database needed — everything is **file-based**
- 🔐 100% **local** — no telemetry, no cloud

---

## 📁 Project Structure

```
.
├── app.py
├── api/                 # API endpoints (e.g., /api/scheduled_events)
├── config/              # App version info
├── core/                # Core logic: SSH, scheduler, execution, utils
├── data/                # Logs for runs and scripts
├── logs/                # Central execution log
├── modules/             # Modular features: hosts, scheduler, scripts, calendar
├── static/              # CSS, JS, images
├── templates/           # Jinja2 HTML templates
├── requirements.txt     # Dependencies
└── README.md
```

---

## 🔧 Setup

### Prerequisites

- Python 3.8+
- `pip`
- OpenSSH client installed
- Works on Linux/macOS/WSL (Windows Subsystem for Linux)

### Installation

```bash
git clone https://github.com/tadjourisamir/hubiwave.git
cd hubiwave

# (Optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Visit: [http://localhost:5000](http://localhost:5000)

---

## 🛠️ Usage Guide

1. ✅ Go to **Hosts** tab → validate or add machines to `hosts.json`.
2. 🐚 Switch to **Scripts** to upload `.sh` or `.py` files.
3. 🕓 Head over to **Scheduler** to set up recurring executions.
4. 📅 View all jobs visually via the **Calendar** tab.

---

## 📦 JSON-based Configuration

| File | Purpose |
|------|---------|
| `hosts.json` | Registered SSH hosts |
| `pending_hosts.json` | Machines waiting for validation |
| `scheduled_events.json` | All planned tasks |
| `metadata.json` | Script descriptions |
| `executions.log` | Logs of manual & scheduled runs |

---

## 🛡️ Security

- Uses **SSH key-based authentication** (never password-based)
- SSH keys stay on your machine (e.g., `~/.ssh/id_rsa`)
- All execution logic is local
- No telemetry, tracking, or remote reporting

---

## 📚 Example Script

```bash
#!/bin/bash
mpv --fs --speed=0.5 ~/Videos/sample.mp4
```

Upload it via the **Scripts** section and select machines to execute.

---

## 🐍 Requirements

Listed in `requirements.txt`:

```txt
flask>=2.2.0
paramiko>=2.11.0
apscheduler>=3.10.0
watchdog>=3.0.0
```

---

## 📝 License

MIT — use freely, credit appreciated.

---

## 👨‍💻 Author

**Samir Tadjouri**  
GitHub: [@tadjourisamir](https://github.com/tadjourisamir)

Feel free to contribute or open issues if you find bugs or want to suggest improvements!
