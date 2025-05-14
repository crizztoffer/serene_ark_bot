import os
import re
import asyncio
import discord
import paramiko
from ark_rcon import ArkRcon

# Load environment variables from Railway
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
SFTP_IP = os.environ["SFTP_IP"]
SFTP_PORT = int(os.environ["SFTP_PORT"])
SFTP_USER = os.environ["SFTP_USER"]
SFTP_PASSWORD = os.environ["SFTP_PASSWORD"]
LOG_PATH = os.environ["LOG_PATH"]
TRIBE_PATH = os.environ["TRIBE_PATH"]
RCON_IP = os.environ["RCON_IP"]
RCON_PORT = int(os.environ["RCON_PORT"])
RCON_PASSWORD = os.environ["RCON_PASSWORD"]

intents = discord.Intents.default()
client = discord.Client(intents=intents)

def fetch_tribe_log_via_sftp():
    try:
        transport = paramiko.Transport((SFTP_IP, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)

        with sftp.open(TRIBE_PATH, "r") as file:
            lines = file.readlines()

        sftp.close()
        transport.close()

        events = []
        for line in lines:
            match = re.match(r"\[(.*?)\] (.*?) was killed by (.*?)!", line)
            if match:
                timestamp, victim, killer = match.groups()
                events.append(f"{timestamp}: {victim} was killed by {killer}")

        return events
    except Exception as e:
        return [f"❌ Error fetching SFTP logs: {str(e)}"]

def fetch_rcon_log():
    try:
        with ArkRcon(RCON_IP, RCON_PORT, RCON_PASSWORD) as rcon:
            return rcon.command("GetTribeLog")
    except Exception as e:
        return f"❌ RCON error: {str(e)}"

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    channel = client.get_channel(CHANNEL_ID)

    # Tribe log via SFTP
    sftp_logs = fetch_tribe_log_via_sftp()
    await channel.send("📄 **Recent Tribe Kills via SFTP:**")
    for entry in sftp_logs[-5:]:
        await channel.send(entry)

    # Live tribe log via RCON
    rcon_log = fetch_rcon_log()
    await channel.send("📡 **Latest Tribe Log via RCON:**")
    await channel.send(f"```\n{rcon_log}\n```")

client.run(DISCORD_TOKEN)
