import os
import warnings
import paramiko
import discord
from discord.ext import tasks
from cryptography.utils import CryptographyDeprecationWarning
from pathlib import Path

# Suppress CryptographyDeprecationWarning from Paramiko
warnings.filterwarnings(
    "ignore",
    category=CryptographyDeprecationWarning,
    module="paramiko.*"
)

# Load environment variables
SFTP_IP = os.environ["SFTP_IP"]
SFTP_PORT = int(os.environ.get("SFTP_PORT", 22))
SFTP_USER = os.environ["SFTP_USER"]
SFTP_PASSWORD = os.environ["SFTP_PASSWORD"]
TRIBE_PATH = os.environ["TRIBE_PATH"]
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
TRIBE_ID = os.environ.get("TRIBE_ID")  # New env variable for filtering logs

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
        return True
    except Exception:
        return False

def extract_tribe_logs(path, tribe_id):
    """
    Extracts death logs from a tribe file or directory for a given tribe ID.

    Args:
        path (str): Path to the .arktribe file or directory containing .arktribe files.
        tribe_id (str): Tribe ID to search for in the files.

    Returns:
        list[str]: List of death log strings.
    """
    tribe_path = Path(path)
    logs = []

    if tribe_path.is_dir():
        files = tribe_path.glob("*.arktribe")
    else:
        files = [tribe_path]

    for file in files:
        try:
            with file.open("rb") as f:
                content = f.read().decode("utf-8", errors="ignore")
                if tribe_id not in content:
                    continue
                # Split logs by each line starting with "Day"
                entries = content.split("Day")
                for entry in entries:
                    if "died" in entry or "was killed by" in entry:
                        # Prepend "Day" back and get first line of entry
                        log_line = "Day" + entry.strip().splitlines()[0]
                        logs.append(log_line)
        except Exception as e:
            print(f"Failed to read {file}: {e}")

    return logs

@tasks.loop(seconds=10)
async def monitor_tribe_log():
    if not fetch_tribe_file():
        return

    logs = extract_tribe_logs(LOCAL_TRIBE_COPY, TRIBE_ID)
    global seen_entries

    for entry in logs:
        if entry not in seen_entries:
            seen_entries.add(entry)

            # Print new dino death to console
            print(f"[DEATH] {entry}")

            # Send to Discord
            channel = client.get_channel(CHANNEL_ID)
            if channel:
                try:
                    await channel.send(f"🦖 Dino Death Alert\n📝 {entry}")
                except Exception:
                    pass

@client.event
async def on_ready():
    monitor_tribe_log.start()

client.run(DISCORD_TOKEN)
