import os
import struct
import warnings
import paramiko
import discord
import logging
import re
from discord.ext import tasks
from cryptography.utils import CryptographyDeprecationWarning

# --- Suppress cryptography deprecation warnings more aggressively ---
warnings.filterwarnings(
    "ignore",
    category=CryptographyDeprecationWarning,
    module="paramiko.*"
)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="paramiko.*"
)

# --- Disable discord.py INFO logs, keep WARNING+ only ---
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('paramiko').setLevel(logging.WARNING)

# Load environment variables
SFTP_IP = os.environ["SFTP_IP"]
SFTP_PORT = int(os.environ.get("SFTP_PORT", 22))
SFTP_USER = os.environ["SFTP_USER"]
SFTP_PASSWORD = os.environ["SFTP_PASSWORD"]
TRIBE_PATH = os.environ["TRIBE_PATH"]
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])

LOCAL_TRIBE_COPY = "tribe_local.arktribe"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

seen_entries = set()

def clean_metadata(raw_text):
    # Remove lines that contain non-printable/control characters or metadata patterns
    # Customize the regex to catch specific unwanted parts.
    lines = raw_text.splitlines()
    clean_lines = []

    for line in lines:
        # Remove lines with unusual control chars or known metadata tags
        if re.search(r'[\x00-\x1F\x7F]|PrimalTribeData|RichColor|TribeName|TribeLog|PlayerDataID', line):
            continue
        # Skip empty or whitespace only lines
        if line.strip() == '':
            continue
        clean_lines.append(line)

    return '\n'.join(clean_lines)

def fetch_tribe_file():
    try:
        transport = paramiko.Transport((SFTP_IP, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.get(TRIBE_PATH, LOCAL_TRIBE_COPY)
        sftp.close()
        transport.close()
        return True
    except Exception:
        return False

def extract_tribe_logs(filepath):
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
                    
                    # Clean the metadata lines out of the log_entry text
                    cleaned_log_entry = clean_metadata(log_entry)
                    
                    # Filter only death-related logs after cleaning
                    # Note: clean_metadata may return multiple lines, check each
                    for line in cleaned_log_entry.splitlines():
                        if any(kw in line.lower() for kw in ["was killed", "was slain", "destroyed by"]):
                            logs.append(line)
                except Exception:
                    break
    except Exception:
        pass
    return logs

@tasks.loop(seconds=10)
async def monitor_tribe_log():
    if not fetch_tribe_file():
        return

    death_logs = extract_tribe_logs(LOCAL_TRIBE_COPY)

    global seen_entries
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        return

    for entry in death_logs:
        if entry not in seen_entries:
            seen_entries.add(entry)

            # Print ONLY death entries to console
            print(f"🦖 Dino Death Alert: {entry}")

            try:
                await channel.send(f"🦖 Dino Death Alert\n📝 {entry}")
            except Exception:
                pass

@client.event
async def on_ready():
    monitor_tribe_log.start()

client.run(DISCORD_TOKEN)
