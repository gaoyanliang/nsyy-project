import logging
from datetime import datetime

import paramiko

logger = logging.getLogger(__name__)


class SshUtil:
    TIMEOUT = 4

    """构造函数"""
    def __init__(self, host: str, username: str, password: str):
        self.ssh_host = host
        self.ssh_username = username
        self.ssh_password = password

        # SSH client
        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()  # Load system SSH host keys (if needed)

        # Connect to the SSH server
        try:
            self.client.connect(host, username=username, password=password, timeout=self.TIMEOUT)
        except paramiko.AuthenticationException:
            logger.error("SSH Util Authentication failed. Please check your credentials.")
            exit(1)
        except paramiko.SSHException as e:
            logger.error(f"SSH Util Unable to establish SSH connection: {str(e)}")
            exit(1)
        except Exception as e:
            logger.error(f"SSH Util Error: {str(e)}")
            exit(1)

    """Close the SSH connection"""
    def __del__(self):
        if self.client is not None:
            self.client.close()
            self.client = None

    """Execute a shell command"""
    def execute_shell_command(self, command, sudo=False):
        # result = {'out': '', 'err': '', 'retval': -1}
        output = ""
        try:
            feed_password = False
            if sudo and self.ssh_username != "root":
                command = f"echo {self.ssh_password} | sudo -S -p '' {command}"  # 更安全的方式
                # 或者保持原样，但后面要正确处理 stdin

            stdin, stdout, stderr = self.client.exec_command(command)

            if feed_password:
                stdin.write(self.ssh_password + '\n')
                stdin.flush()
                stdin.close()  # ← 关键！必须关闭 stdin

            # 现在可以安全读取输出
            output = stdout.read().decode('utf-8')
            # err = stderr.read().decode('utf-8')
            # retval = stdout.channel.recv_exit_status()
            #
            # print(f"Debugging: command: {command}")
            # print(f"Debugging: output:\n{output}")
            # print(f"Debugging: errors:\n{err}")
            # print(f"Debugging: exit code: {retval}")
        except Exception as e:
            logger.error(f"SSH Util Error executing command: {str(e)}")

        return output


# # SSH connection details
# ssh_host = "192.168.124.128"
# ssh_username = "root"
# ssh_password = "111111"


# if __name__ == "__main__":
#     ssh = SshUtil(ssh_host, ssh_username, ssh_password)
#     ssh.execute_shell_command("pwd")
#     # ssh.execute_shell_command("whoami", sudo=True)
#     # ssh.execute_shell_command("python3 -V", sudo=True)
#     ssh.execute_shell_command(f"cd /opt/mlmmjadmin-3.1.8/tools/; python3 /opt/mlmmjadmin-3.1.8/tools/maillist_admin.py update tg1@nsyy.com only_subscriber_can_post=yes disable_subscription=no", sudo=True)
#     ssh.execute_shell_command(f"cd /opt/mlmmjadmin-3.1.8/tools/; python3 /opt/mlmmjadmin-3.1.8/tools/maillist_admin.py info tg1@nsyy.com")
#     del ssh








