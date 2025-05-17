import os
import time
import struct
import warnings
import paramiko
import discord
from discord.ext import tasks

# Suppress CryptographyDeprecationWarning from paramiko
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="paramiko.pkey"
)

# Environment variables
SFTP_IP = os.environ["SFTP_IP"]
SFTP_PORT = int(os.environ.get("SFTP_PORT", 22))
SFTP_USER = os.environ["SFTP_USER"]
SFTP_PASSWORD = os.environ["SFTP_PASSWORD"]
TRIBE_PATH = os.environ["TRIBE_PATH"]  # remote path on server, e.g., /ShooterGame/Saved/Tribes/12345678.arktribe
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

LOCAL_TRIBE_COPY = "tribe_local.arktribe"

intents = discord.Intents.default()
client = discord.Client(intents=intents)

seen_entries = set()

def fetch_tribe_file():
    try:
        transport = paramiko.Transport((SFTP_IP, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)

        sftp.get(TRIBE_PATH, LOCAL_TRIBE_COPY)

        sftp.close()
        transport.close()
        print("[SFTP] Tribe file fetched.")
        return True
    except Exception as e:
        print(f"[SFTP ERROR] {e}")
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
                    if "was killed by" in log_entry or DEBUG:
                        logs.append(log_entry)
                except:
                    break
    except Exception as e:
        print(f"[ERROR] Failed to read tribe log: {e}")
    return logs

@tasks.loop(seconds=10)
async def monitor_tribe_log():
    if not fetch_tribe_file():
        return

    logs = extract_tribe_logs(LOCAL_TRIBE_COPY)
    global seen_entries

    for entry in logs:
        if DEBUG:
            print("[DEBUG] Log Entry:", entry)
        if entry not in seen_entries and "was killed by" in entry:
            seen_entries.add(entry)
            msg = f"🦖 Dino Death Alert\n📝 {entry}"
            channel = client.get_channel(CHANNEL_ID)
            if channel:
                await channel.send(msg)
            else:
                print("[DISCORD ERROR] Channel not found")

@client.event
async def on_ready():
    print(f"[BOT] Connected as {client.user}")
    monitor_tribe_log.start()

client.run(DISCORD_TOKEN)
