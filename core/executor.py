import paramiko
import os
import time
import threading
import shlex
import uuid
from datetime import datetime
from core.ssh_service import test_ssh_connection, KEY_PATH
from core.utils import load_hosts

SCRIPTS_DIR = "modules/scripts/scripts_drive"
LOG_FILE = "logs/executions.log"


def log_execution(ip, task_id, filename, status, error=None):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        timestamp = datetime.now().isoformat()
        entry = f"{timestamp} | {ip} | {filename} | {task_id} | {status}"
        if error:
            entry += f" | {error}"
        f.write(entry + "\n")


def kill_remote_process(ip, user, port, pid_file):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pkey = paramiko.RSAKey.from_private_key_file(KEY_PATH)
        ssh.connect(hostname=ip, port=port, username=user, pkey=pkey)

        stdin, stdout, stderr = ssh.exec_command(f"cat {pid_file}")
        pid = stdout.read().decode().strip()

        if pid:
            kill_cmd = f"pkill -TERM -P {pid}; kill -9 {pid}; rm -f {pid_file}"
        else:
            kill_cmd = "pkill -f 'mpv'"

        ssh.exec_command(kill_cmd)
        ssh.close()
        print(f"Killed process on {ip} ({'PID' if pid else 'fallback'})")

    except Exception as e:
        print(f"Failed to kill process on {ip}: {e}")


def prepare_ssh(ip, user, port, max_time=1.5):
    deadline = time.time() + max_time
    while time.time() < deadline:
        if test_ssh_connection(ip, user, port):
            return True
        time.sleep(0.2)
    return False


def run_task(task, ip, execution_index=0, executions_per_cycle=1, execution_spacing=0):
    task_type = task.get("type", "command")
    script_name = task.get("filename", "")
    remote_name = task.get("remote_name") or "script.sh"
    timeout = float(task.get("timeout", 0))
    task_id = task.get("id", "unknown-task")
    detach = task.get("detach", False) if task_type == "command" else False

    hosts = load_hosts()
    host = next((h for h in hosts if h["ip"] == ip), None)
    if not host:
        print(f"Host not found: {ip}")
        return

    user = host.get("user", "root")
    port = int(host.get("port", 22))

    print(f"Preparing SSH to {ip}...")
    deadline = time.time() + 3
    while time.time() < deadline:
        if test_ssh_connection(ip, user, port):
            break
        time.sleep(0.2)
    else:
        print(f"SSH unreachable: {ip}")
        return

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pkey = paramiko.RSAKey.from_private_key_file(KEY_PATH)
        ssh.connect(hostname=ip, port=port, username=user, pkey=pkey)
        sftp = ssh.open_sftp()

        if task_type == "script" and script_name:
            local_path = os.path.join(SCRIPTS_DIR, script_name)
            remote_path = f"/tmp/{remote_name}"
            sftp.put(local_path, remote_path)
            sftp.chmod(remote_path, 0o755)
            command = f"{remote_path}"
        elif task_type == "command":
            command = task.get("command", "")
        else:
            raise ValueError("Missing or unknown task type")

        user_home = f"/home/{user}"
        xauth = f"{user_home}/.Xauthority"
        command = command.replace("~", user_home)
        base_cmd = f"export DISPLAY=:0; export XAUTHORITY={xauth}; {command}"
        pid_file = f"/tmp/pid_{task_id.replace('-', '')}_{ip.replace('.', '')}_{uuid.uuid4().hex[:6]}.txt"

        if detach:
            full_cmd = f'nohup bash -c {shlex.quote(base_cmd)} > /dev/null 2>&1 & echo $! > {pid_file}'
            ssh.exec_command(full_cmd)
            print(f"Detached command launched on {ip}")
            if timeout > 0:
                def delayed_kill():
                    time.sleep(timeout)
                    kill_remote_process(ip, user, port, pid_file)
                    print(f"Timeout reached — killed detached process on {ip}")
                threading.Thread(target=delayed_kill, daemon=True).start()
        else:
            full_cmd = (
                f"export DISPLAY=:0; export XAUTHORITY={xauth}; "
                f"bash -c '{command}' & echo $! > {pid_file}; wait $(cat {pid_file})"
            )
            stdin, stdout, stderr = ssh.exec_command(full_cmd)

            if timeout > 0:
                def delayed_kill():
                    time.sleep(timeout)
                    kill_remote_process(ip, user, port, pid_file)
                    print(f"Timeout reached — killed foreground process on {ip}")
                threading.Thread(target=delayed_kill, daemon=True).start()

            exit_status = stdout.channel.recv_exit_status()
            print(f"Task completed on {ip} (exit: {exit_status})")

            if execution_index < executions_per_cycle - 1 and execution_spacing > 0:
                print(f"Waiting {execution_spacing}s before next execution")
                time.sleep(execution_spacing)

        sftp.close()
        ssh.close()

    except Exception as e:
        print(f"Error during execution on {ip}: {e}")


def run_cycle(task, ips, cycle_index):
    task_type = task.get("type", "command")
    script_name = task.get("filename", "")
    remote_name = task.get("remote_name") or "script.sh"
    timeout = float(task.get("timeout", 0))
    task_id = task.get("id", "unknown-task")
    detach = task.get("detach", False) if task_type == "command" else False

    hosts = load_hosts()
    host_map = {h["ip"]: h for h in hosts}

    def execute_on_ip(ip):
        host = host_map.get(ip)
        if not host:
            print(f"Host not found: {ip}")
            return

        user = host.get("user", "root")
        port = int(host.get("port", 22))

        print(f"Preparing SSH for {ip} (cycle {cycle_index})...")
        deadline = time.time() + 3
        while time.time() < deadline:
            if test_ssh_connection(ip, user, port):
                break
            time.sleep(0.2)
        else:
            print(f"SSH unreachable: {ip}")
            return

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            pkey = paramiko.RSAKey.from_private_key_file(KEY_PATH)
            ssh.connect(hostname=ip, port=port, username=user, pkey=pkey)
            sftp = ssh.open_sftp()

            if task_type == "script" and script_name:
                local_path = os.path.join(SCRIPTS_DIR, script_name)
                remote_path = f"/tmp/{remote_name}"
                sftp.put(local_path, remote_path)
                sftp.chmod(remote_path, 0o755)
                command = f"{remote_path}"
            elif task_type == "command":
                command = task.get("command", "")
            else:
                raise ValueError("Missing or unknown task type")

            user_home = f"/home/{user}"
            xauth = f"{user_home}/.XAUTHORITY"
            command = command.replace("~", user_home)
            pid_file = f"/tmp/pid_{task_id.replace('-', '')}_{ip.replace('.', '')}_{uuid.uuid4().hex[:6]}.txt"

            if detach:
                full_cmd = f'nohup bash -c {shlex.quote(command)} > /dev/null 2>&1 & echo $! > {pid_file}'
                ssh.exec_command(full_cmd)
            else:
                full_cmd = (
                    f"export DISPLAY=:0; export XAUTHORITY={xauth}; "
                    f"bash -c '{command}' & echo $! > {pid_file}; wait $(cat {pid_file})"
                )
                stdin, stdout, stderr = ssh.exec_command(full_cmd)

                def delayed_kill():
                    time.sleep(timeout)
                    kill_remote_process(ip, user, port, pid_file)

                if timeout > 0:
                    threading.Thread(target=delayed_kill, daemon=True).start()

                exit_status = stdout.channel.recv_exit_status()
                print(f"{ip} — finished (exit {exit_status})")

            sftp.close()
            ssh.close()

        except Exception as e:
            print(f"Error during execution on {ip}: {e}")

    print(f"Launching parallel cycle {cycle_index} for {len(ips)} IP(s)...")
    threads = []
    for ip in ips:
        t = threading.Thread(target=execute_on_ip)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print(f"Parallel cycle {cycle_index} completed")
