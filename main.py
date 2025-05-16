import os
import warnings
import time
import paramiko
import discord
from discord.ext import commands, tasks
from arkparse import ArkTribe  # Correct import
from cryptography.utils import CryptographyDeprecationWarning

# Suppress TripleDES deprecation warnings
warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)

# Load environment variables
SFTP_IP = os.environ["SFTP_IP"]
SFTP_PORT = int(os.environ.get("SFTP_PORT", 22))
SFTP_USER = os.environ["SFTP_USER"]
SFTP_PASSWORD = os.environ["SFTP_PASSWORD"]
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# Default to a local temp file
TRIBE_PATH = "temp.arktribe"
# Remote directory for tribe files
REMOTE_DIR = "/ShooterGame/Saved/SavedArks"

seen_logs = set()

# Enable message content intent
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

def list_arktribe_files():
    try:
        transport = paramiko.Transport((SFTP_IP, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)

        files = sftp.listdir(REMOTE_DIR)
        arktribe_files = [f for f in files if f.endswith(".arktribe")]

        sftp.close()
        transport.close()

        print(f"[SFTP] Found .arktribe files: {arktribe_files}")
        return arktribe_files
    except Exception as e:
        print(f"[SFTP ERROR] {e}")
        return []

def fetch_tribe_file(remote_file):
    try:
        transport = paramiko.Transport((SFTP_IP, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)

        remote_path = f"{REMOTE_DIR}/{remote_file}"
        sftp.get(remote_path, TRIBE_PATH)

        sftp.close()
        transport.close()
        print(f"[SFTP] Successfully downloaded {remote_path} to {TRIBE_PATH}")
        return True
    except Exception as e:
        print(f"[SFTP ERROR] {e}")
        return False

def is_dino_death(msg):
    return "tame" in msg.lower() and any(
        k in msg.lower() for k in ["was killed", "was slain", "has died"]
    )

def get_new_dino_deaths():
    deaths = []
    try:
        with open(TRIBE_PATH, "rb") as f:
            data = f.read()
        tribe = ArkTribe(data)  # <-- Fix: pass bytes instead of file object
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
    arktribe_files = list_arktribe_files()
    if not arktribe_files:
        print("[SFTP] No .arktribe files found to download.")
        return

    if fetch_tribe_file(arktribe_files[0]):
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
import os
import warnings
import time
import paramiko
import discord
from discord.ext import commands, tasks
from arkparse import ArkTribe  # Correct import
from cryptography.utils import CryptographyDeprecationWarning

# Suppress TripleDES deprecation warnings
warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)

# Load environment variables
SFTP_IP = os.environ["SFTP_IP"]
SFTP_PORT = int(os.environ.get("SFTP_PORT", 22))
SFTP_USER = os.environ["SFTP_USER"]
SFTP_PASSWORD = os.environ["SFTP_PASSWORD"]
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# Default to a local temp file
TRIBE_PATH = "temp.arktribe"
# Remote directory for tribe files
REMOTE_DIR = "/ShooterGame/Saved/SavedArks"

seen_logs = set()

# Enable message content intent
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

def list_arktribe_files():
    try:
        transport = paramiko.Transport((SFTP_IP, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)

        files = sftp.listdir(REMOTE_DIR)
        arktribe_files = [f for f in files if f.endswith(".arktribe")]

        sftp.close()
        transport.close()

        print(f"[SFTP] Found .arktribe files: {arktribe_files}")
        return arktribe_files
    except Exception as e:
        print(f"[SFTP ERROR] {e}")
        return []

def fetch_tribe_file(remote_file):
    try:
        transport = paramiko.Transport((SFTP_IP, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)

        remote_path = f"{REMOTE_DIR}/{remote_file}"
        sftp.get(remote_path, TRIBE_PATH)

        sftp.close()
        transport.close()
        print(f"[SFTP] Successfully downloaded {remote_path} to {TRIBE_PATH}")
        return True
    except Exception as e:
        print(f"[SFTP ERROR] {e}")
        return False

def is_dino_death(msg):
    return "tame" in msg.lower() and any(
        k in msg.lower() for k in ["was killed", "was slain", "has died"]
    )

def get_new_dino_deaths():
    deaths = []
    try:
        # Pass the path string to ArkTribe, not an open file
        tribe = ArkTribe(TRIBE_PATH)
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
    arktribe_files = list_arktribe_files()
    if not arktribe_files:
        print("[SFTP] No .arktribe files found to download.")
        return

    # Always fetch the first available tribe file
    if fetch_tribe_file(arktribe_files[0]):
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
