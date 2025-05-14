import os
import io
import paramiko
from dotenv import load_dotenv
from arkpy.tribe import Tribe

# Load environment variables
load_dotenv()

SFTP_HOST = os.getenv("SFTP_IP")
SFTP_PORT = int(os.getenv("SFTP_PORT", 22))
SFTP_USER = os.getenv("SFTP_USER")
SFTP_PASS = os.getenv("SFTP_PASSWORD")
TRIBE_PATH = os.getenv("TRIBE_PATH", "/home/container/ShooterGame/Saved/SavedArks/")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

def debug(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")

def sftp_connect():
    """Establish and return an SFTP client."""
    transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    transport.connect(username=SFTP_USER, password=SFTP_PASS)
    debug("Connected to SFTP.")
    return paramiko.SFTPClient.from_transport(transport)

def list_tribes():
    """Download and parse .arktribe files using arkpy."""
    try:
        sftp = sftp_connect()
        files = sftp.listdir(TRIBE_PATH)
        for filename in files:
            if filename.endswith(".arktribe"):
                full_path = os.path.join(TRIBE_PATH, filename)
                debug(f"Reading tribe file: {filename}")
                with sftp.open(full_path, "rb") as f:
                    data = f.read()
                    try:
                        tribe = Tribe.from_bytes(data)
                        print(f"Tribe Name: {tribe.name}")
                        print(f"Tribe ID: {tribe.id}")
                        print(f"Members: {[m.name for m in tribe.members]}")
                        print("-" * 40)
                    except Exception as e:
                        print(f"[ERROR] Failed to parse {filename}: {e}")
        sftp.close()
    except Exception as e:
        print(f"[ERROR] SFTP error: {e}")

if __name__ == "__main__":
    list_tribes()
