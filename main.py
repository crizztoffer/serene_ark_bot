import os
import warnings
import asyncio
import paramiko
import discord
from discord.ext import commands, tasks
from arkparse import ArkTribe  # <-- Correct import
from cryptography.utils import CryptographyDeprecationWarning

# Suppress TripleDES deprecation warnings
warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)

# Load environment variables
SFTP_IP = os.environ["SFTP_IP"]
SFTP_PORT = int(os.environ.get("SFTP_PORT", 22))
SFTP_USER = os.environ["SFTP_USER"]
SFTP_PASSWORD = os.environ["SFTP_PASSWORD"]
LOG_PATH = os.environ["LOG_PATH"]
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
