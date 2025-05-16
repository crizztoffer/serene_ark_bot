import os
import warnings
import asyncio
import paramiko
import discord
from discord.ext import commands, tasks
from arkparse import ArkTribe
from cryptography.utils import CryptographyDeprecationWarning

# Suppress TripleDES deprecation warnings
warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)

# Load environment variables
SFTP_IP = os.environ["SFTP_IP"]
SFTP_PORT = int(os.environ.get("SFTP_PORT", 22))
SFTP_USER = os.environ["SFTP_USER"]
SFTP_PASSWORD = os.environ["SFTP_PASSWORD"]
LOG_PATH = os.environ["LOG_PATH"]  # e.g. "/home/container/ShooterGame/Saved/SavedArks/1234567890.arktribe"
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

LOCAL_FILE = "temp.arktribe"
seen_logs = set()

# Enable message content intent
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

def is_dino_death(msg):
    return "tame" in msg.lower() and any(
        k in msg.lower() for k in ["was killed", "was slain", "has died"]
    )

def check_path_steps(sftp, path):
    parts = path.strip("/").split("/")
    current_path = ""
    for part in parts:
        current_path += "/" + part
        try:
            sftp.stat(current_path)
            print(f"[SFTP PATH CHECK] Exists: {current_path}")
        except FileNotFoundError:
            print(f"[SFTP PATH CHECK] NOT FOUND: {current_path}")
            break

def fetch_tribe_file():
    try:
        transport = paramiko.Transport((SFTP_IP, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)

        # DEBUG: Check each step of the path to debug missing directories/files
        if DEBUG:
            check_path_steps(sftp, LOG_PATH)

        sftp.get(LOG_PATH, LOCAL_FILE)
        sftp.close()
        transport.close()
        print("[SFTP] File fetched successfully")
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
