import os
import io
import discord
import asyncio
import paramiko
from arkgame.tribe import ArkTribe
from dotenv import load_dotenv

# Load Railway or local .env variables
load_dotenv()

# ENV variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
SFTP_HOST = os.getenv("SFTP_IP")
SFTP_PORT = int(os.getenv("SFTP_PORT", 22))
SFTP_USER = os.getenv("SFTP_USER")
SFTP_PASS = os.getenv("SFTP_PASSWORD")
LOG_PATH = os.getenv("LOG_PATH", "/home/container/ShooterGame/Saved/Logs/ShooterGame.log")
TRIBE_PATH = os.getenv("TRIBE_PATH", "/home/container/ShooterGame/Saved/SavedArks/")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tribe_lookup = {}

def sftp_connect():
    """Establish an SFTP connection using Paramiko."""
    transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    transport.connect(username=SFTP_USER, password=SFTP_PASS)
    return paramiko.SFTPClient.from_transport(transport)

def fetch_tribes():
    """Load all .arktribe files and build a tribe lookup dictionary."""
    global tribe_lookup
    try:
        sftp = sftp_connect()
        for filename in sftp.listdir(TRIBE_PATH):
            if filename.endswith(".arktribe"):
                path = os.path.join(TRIBE_PATH, filename)
                with sftp.open(path, "rb") as f:
                    data = f.read()
                    try:
                        tribe = ArkTribe.from_file(io.BytesIO(data))
                        if tribe.tribe_name:
                            tribe_lookup[tribe.tribe_id] = tribe.tribe_name
                            if DEBUG:
                                print(f"[DEBUG] Loaded tribe: {tribe.tribe_name} (ID: {tribe.tribe_id})")
                    except Exception as e:
                        print(f"[ERROR] Failed to parse {filename}: {e}")
        sftp.close()
    except Exception as e:
        print(f"[ERROR] SFTP tribe fetch failed: {e}")

async def watch_logs():
    """Continuously check ShooterGame.log for new death messages."""
    if not DEBUG:
        await client.wait_until_ready()
        channel = client.get_channel(CHANNEL_ID)
    last_line = ""

    while True:
        try:
            sftp = sftp_connect()
            with sftp.open(LOG_PATH, "rb") as f:
                content = f.read().decode("utf-8", errors="ignore")
                lines = content.splitlines()

                # Only get new lines since last check
                if last_line in lines:
                    new_lines = lines[lines.index(last_line) + 1:]
                else:
                    new_lines = lines[-20:]

                for line in new_lines:
                    if "died" in line.lower() or "killed" in line.lower():
                        for tribe_id, tribe_name in tribe_lookup.items():
                            if str(tribe_id) in line:
                                message = f"🦖 A dino from **{tribe_name}** died!\n```{line.strip()}```"
                                if DEBUG:
                                    print("[DEBUG]", message)
                                else:
                                    await channel.send(message)
                                break

                if lines:
                    last_line = lines[-1]
            sftp.close()

        except Exception as e:
            print(f"[ERROR] Log read failed: {e}")

        await asyncio.sleep(30)

@client.event
async def on_ready():
    print(f"[Discord] Logged in as {client.user}")
    fetch_tribes()
    print(f"[ARK] Loaded {len(tribe_lookup)} tribes.")
    client.loop.create_task(watch_logs())

if DEBUG:
    print("[DEBUG] Debug mode enabled. Running without Discord connection.")
    fetch_tribes()
    asyncio.run(watch_logs())
else:
    client.run(DISCORD_TOKEN)

