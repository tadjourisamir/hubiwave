import json
import os

HOSTS_FILE = "modules/hosts/data/hosts.json"

def load_hosts():
    if os.path.exists(HOSTS_FILE):
        with open(HOSTS_FILE, "r") as f:
            return json.load(f)
    return []
