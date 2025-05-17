import os
import struct
import warnings
import re
import paramiko
import requests

# Suppress Paramiko's CryptographyDeprecationWarning
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="paramiko.pkey"
)

# Load configuration from environment variables
SFTP_IP = os.environ["SFTP_IP"]
SFTP_PORT = int(os.environ.get("SFTP_PORT", 22))
SFTP_USER = os.environ["SFTP_USER"]
SFTP_PASSWORD = os.environ["SFTP_PASSWORD"]
TRIBE_PATH = os.environ["TRIBE_PATH"]
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1373237680116203591/oA-a9MoBXMjAhKIkdGJP-CAidO9z2642Ormq1SWrpc1k5XpUT8_khFqFWocRWu2FiV5o"
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

LOCAL_TRIBE_COPY = "tribe_local.arktribe"
CHECK_INTERVAL = 3  # seconds

seen_entries = set()
first_run = True

# --- CATEGORY DEFINITIONS ---
LOG_PATTERNS = {
    "death": [
        r"\bwas killed by\b",
        r"\bwas slain by\b",
        r"\bdied\b",
    ],
}

def classify_log(entry):
    for category, patterns in LOG_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, entry, re.IGNORECASE):
                return category
    return None

def fetch_tribe_file():
    try:
        transport = paramiko.Transport((SFTP_IP, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.get(TRIBE_PATH, LOCAL_TRIBE_COPY)
        sftp.close()
        transport.close()
        return True
    except Exception as e:
        if DEBUG:
            print(f"[ERROR] SFTP fetch failed: {e}")
        return False

def extract_tribe_logs(filepath, category_filter=None):
    logs = []
    try:
        with open(filepath, "rb") as f:
            data = f.read()
            pos = 0
            while pos < len(data) - 4:
                try:
                    length = struct.unpack_from("<i", data, pos)[0]
                    pos += 4
                    if length <= 0 or pos + length > len(data):
                        continue
                    string_bytes = data[pos:pos + length - 1]
                    pos += length
                    log_entry = string_bytes.decode("utf-8", errors="ignore")
                    if category_filter:
                        if classify_log(log_entry) == category_filter:
                            logs.append(log_entry)
                    else:
                        logs.append(log_entry)
                except Exception:
                    break
    except Exception as e:
        if DEBUG:
            print(f"[ERROR] Reading tribe file failed: {e}")
    return logs

def clean_log_entry(entry):
    # Remove timestamp prefix (e.g., "Day 123, 12:34:56: ")
    entry = re.sub(r"^Day \d+, \d{2}:\d{2}:\d{2}:\s*", "", entry)
    # Remove RichColor tag
    entry = re.sub(r"<RichColor Color=\"[^\"]+\">", "", entry)
    # Remove closing tag
    entry = entry.replace("</>", "")
    return entry

def send_discord_webhook(message):
    try:
        response = requests.post(DISCORD_WEBHOOK, json={"content": message})
        if response.status_code != 204:
            if DEBUG:
                print(f"[ERROR] Webhook failed: {response.status_code} {response.text}")
    except Exception as e:
        if DEBUG:
            print(f"[ERROR] Webhook exception: {e}")

def monitor_loop():
    global first_run, seen_entries
    import time

    while True:
        if not fetch_tribe_file():
            time.sleep(CHECK_INTERVAL)
            continue

        logs = extract_tribe_logs(LOCAL_TRIBE_COPY, category_filter="death")

        if first_run:
            seen_entries.update(logs)
            first_run = False
        else:
            for entry in logs:
                if entry not in seen_entries:
                    seen_entries.add(entry)
                    cleaned = clean_log_entry(entry)
                    msg = f"🦖 Dino Death Alert\n{cleaned}"
                    if DEBUG:
                        print(msg)
                    send_discord_webhook(msg)

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    monitor_loop()
