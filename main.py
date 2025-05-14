import os
import re
import time
import paramiko
import discord
import asyncio
from discord.ext import commands
from arkpy import ark

# Load environment variables from Railway
RCON_HOST = os.getenv("RCON_IP")
RCON_PORT = int(os.getenv("RCON_PORT", 27020))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
SFTP_HOST = os.getenv("SFTP_IP")
SFTP_PORT = int(os.getenv("SFTP_PORT", 22))
SFTP_USER = os.getenv("SFTP_USER")
SFTP_PASS = os.getenv("SFTP_PASSWORD")
LOG_PATH = os.getenv("LOG_PATH", "/home/container/ShooterGame/Saved/Logs/ShooterGame.log")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
TRIBE_PATH = os.getenv("TRIBE_PATH")  # Fetching TRIBE_PATH from Railway environment variable
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

bot = commands.Bot(command_prefix="!")

# Regular expression to detect dino death lines
DINO_DEATH_REGEX = re.compile(r"TamedDino Died: (.*?) \(Tribe (.*?)\).+? by (.*?) \(.*?\)")

# Read Tribe Information (from .arktribe file)
def get_tribe_info(file_path):
    tribe = ark.ArkTribe(file_path)
    members = {mid.value: name.value for name, mid in tribe.members}
    return members

# Map tribe members from the .arktribe file
tribe_members = get_tribe_info(TRIBE_PATH)

async def monitor_logs():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SFTP_HOST, port=SFTP_PORT, username=SFTP_USER, password=SFTP_PASS)
    sftp = client.open_sftp()

    try:
        # Open the log file
        with sftp.open(LOG_PATH, "r") as logfile:
            logfile.seek(0, 2)  # Move to the end of the file

            while True:
                line = logfile.readline()
                if not line:
                    await asyncio.sleep(1)
                    continue

                match = DINO_DEATH_REGEX.search(line)
                if match:
                    dino, tribe_name, killer = match.groups()

                    # Check if the tribe name is in the members list
                    if tribe_name in tribe_members:
                        if DEBUG:
                            print(f"[DEBUG] Dino: {dino}, Tribe: {tribe_name}, Killed By: {killer}")
                        else:
                            channel = bot.get_channel(DISCORD_CHANNEL_ID)
                            if channel:
                                await channel.send(
                                    f"🦖 **{tribe_name}** lost a **{dino}**!\\nKilled by: {killer}"
                                )
    finally:
        sftp.close()
        client.close()

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    bot.loop.create_task(monitor_logs())

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
