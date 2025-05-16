import os
import time
import re
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
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

REMOTE_LOG_PATH = "/ShooterGame/Saved/Logs/ShooterGame.log"
LOCAL_LOG_COPY = "ShooterGame_local.log"

death_pattern = re.compile(
    r"\[(?P<datetime>\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2})\].*?'(?P<tribe>.*?)'s\s(?P<dino>.*?)\swas\skilled\sby\s(?P<killer>.*)"
)

intents = discord.Intents.default()
client = discord.Client(intents=intents)

seen_lines = set()

def fetch_log_file():
    try:
        transport = paramiko.Transport((SFTP_IP, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)

        sftp.get(REMOTE_LOG_PATH, LOCAL_LOG_COPY)

        sftp.close()
        transport.close()
        print("[SFTP] Log file fetched.")
        return True
    except Exception as e:
        print(f"[SFTP ERROR] {e}")
        return False

@tasks.loop(seconds=10)
async def monitor_log():
    if not fetch_log_file():
        return

    try:
        with open(LOCAL_LOG_COPY, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        global seen_lines

        if DEBUG:
            # In debug mode, print ALL matched death messages (past and present)
            print("[DEBUG] Printing all dino death entries in log:")
            for line in lines:
                match = death_pattern.search(line)
                if match:
                    msg = (
                        f"🦖 Dino Death Alert\n"
                        f"📅 Time: {match.group('datetime')}\n"
                        f"🏹 Tribe: {match.group('tribe')}\n"
                        f"🦕 Dino: {match.group('dino')}\n"
                        f"☠️ Killed by: {match.group('killer')}"
                    )
                    print(msg)
            # In debug, we do not update seen_lines, to keep printing all on every loop

        else:
            # In non-debug mode, only send new messages (never seen before)
            for line in lines:
                if line in seen_lines:
                    continue

                match = death_pattern.search(line)
                if match:
                    seen_lines.add(line)
                    msg = (
                        f"🦖 Dino Death Alert\n"
                        f"📅 Time: {match.group('datetime')}\n"
                        f"🏹 Tribe: {match.group('tribe')}\n"
                        f"🦕 Dino: {match.group('dino')}\n"
                        f"☠️ Killed by: {match.group('killer')}"
                    )
                    channel = client.get_channel(CHANNEL_ID)
                    if channel:
                        await channel.send(msg)
                    else:
                        print("[DISCORD ERROR] Channel not found")

    except Exception as e:
        print(f"[ERROR] Reading local log file: {e}")

@client.event
async def on_ready():
    print(f"[BOT] Connected as {client.user}")
    monitor_log.start()

client.run(DISCORD_TOKEN)
