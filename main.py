import os
import time
import asyncio
import warnings
import paramiko
import discord
from discord.ext import commands, tasks
from arkparse import ArkTribe

# Suppress deprecation warnings (optional)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Load environment variables
SFTP_IP = os.environ["SFTP_IP"]
SFTP_PORT = int(os.environ.get("SFTP_PORT", "22"))
SFTP_USER = os.environ["SFTP_USER"]
SFTP_PASSWORD = os.environ["SFTP_PASSWORD"]
LOG_PATH = os.environ["LOG_PATH"]
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# Local temp file for download
LOCAL_FILE = "temp.arktribe"
seen_logs = set()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def is_dino_death(msg):
    return "tame" in msg.lower() and any(
        k in msg.lower() for k in ["was killed", "was slain", "has died"]
    )

def fetch_tribe_file():
    try:
        transport = paramiko.Transport((SFTP_IP, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.get(LOG_PATH, LOCAL_FILE)
        sftp.close()
        transport.close()
        return True
    except Exception as e:
        print(f"[SFTP ERROR] {e}")
        return False

def get_new_dino_deaths():
    deaths = []
    try:
        with open(LOCAL_FILE, "rb") as f:
            tribe = ArkTribe(f)
        for entry in tribe.log:
            msg = getattr(entry, "message", str(entry))
            if msg not in seen_logs:
                seen_logs.add(msg)
                if is_dino_death(msg):
                    deaths.append(msg)
    except Exception as e:
        print(f"[PARSE ERROR] {e}")
    return deaths

@tasks.loop(seconds=10)
async def monitor_tribe_file():
    if fetch_tribe_file():
        deaths = get_new_dino_deaths()
        if deaths:
            for msg in deaths:
                output = f"🦖 Dino Death Alert: {msg}"
                if DEBUG:
                    print(output)
                else:
                    channel = bot.get_channel(CHANNEL_ID)
                    if channel:
                        await channel.send(output)
                    else:
                        print("[DISCORD ERROR] Channel not found")

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    monitor_tribe_file.start()

bot.run(DISCORD_TOKEN)
