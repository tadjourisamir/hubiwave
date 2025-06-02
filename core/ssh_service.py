import os
import paramiko
import time
import logging

KEY_PATH = os.path.expanduser("~/.ssh/id_rsa")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def ensure_ssh_key():
    if not os.path.exists(KEY_PATH):
        os.system(f'ssh-keygen -t rsa -N "" -f {KEY_PATH}')
        logger.info("✅ SSH key generated.")
    else:
        logger.info("🔑 SSH key already exists.")

def load_private_key(key_path=KEY_PATH):
    try:
        return paramiko.RSAKey.from_private_key_file(key_path)
    except Exception as e:
        logger.error(f"❌ Failed to load private key: {e}")
        return None

def auto_copy_key(ip, user, port=22, key_path=KEY_PATH):
    pub_key_path = key_path + ".pub"
    try:
        with open(pub_key_path, 'r') as f:
            pub_key = f.read().strip()
    except Exception as e:
        logger.error(f"❌ Failed to read public key: {e}")
        return False

    cmd = (
        f"ssh -o StrictHostKeyChecking=no -p {port} {user}@{ip} "
        f"\"mkdir -p ~/.ssh && chmod 700 ~/.ssh && "
        f"echo '{pub_key}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys\""
    )

    result = os.system(cmd)
    if result == 0:
        logger.info(f"✅ SSH key copied to {ip}")
        return True
    else:
        logger.error(f"❌ SSH key copy to {ip} failed.")
        return False

def test_ssh_connection(ip, user, port=22, key_path=KEY_PATH, retries=3, delay=2):
    pkey = load_private_key(key_path)
    if not pkey:
        return False

    for attempt in range(1, retries + 1):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=ip, port=port, username=user, pkey=pkey, timeout=3)
            ssh.close()
            logger.info(f"✅ SSH connection to {ip} successful.")
            return True
        except Exception as e:
            logger.warning(f"⚠️ SSH attempt {attempt} failed on {ip}: {e}")
            time.sleep(delay)

    logger.error(f"⛔ All SSH attempts failed for {ip}")
    return False

def get_mac_address(ip, user, port=22, key_path=KEY_PATH, timeout=5):
    pkey = load_private_key(key_path)
    if not pkey:
        return None

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(hostname=ip, port=port, username=user, pkey=pkey, timeout=timeout)

        stdin, stdout, _ = ssh.exec_command("ls /sys/class/net/")
        interfaces = stdout.read().decode().split()

        for iface in interfaces:
            stdin, stdout, _ = ssh.exec_command(f"cat /sys/class/net/{iface}/address")
            mac = stdout.read().decode().strip()
            if mac and len(mac.split(":")) == 6 and mac != "00:00:00:00:00:00":
                return mac
    except Exception as e:
        logger.error(f"[⚠️ MAC ERROR] on {ip}: {e}")
    finally:
        ssh.close()

    return None
