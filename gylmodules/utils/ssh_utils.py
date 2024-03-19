import paramiko


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
            self.client.connect(ssh_host, username=ssh_username, password=ssh_password, timeout=self.TIMEOUT)
        except paramiko.AuthenticationException:
            print("Authentication failed. Please check your credentials.")
            exit(1)
        except paramiko.SSHException as e:
            print(f"Unable to establish SSH connection: {str(e)}")
            exit(1)
        except Exception as e:
            print(f"Error: {str(e)}")
            exit(1)

    """Close the SSH connection"""
    def __del__(self):
        if self.client is not None:
            self.client.close()
            self.client = None
        print("Close the SSH connection!")

    """Execute a shell command"""
    def execute_shell_command(self, command, sudo=False) -> object:
        output = ""
        try:
            feed_password = False
            if sudo and self.ssh_username != "root":
                command = "sudo -S -p '' %s" % command
                feed_password = self.ssh_password is not None and len(self.ssh_password) > 0

            stdin, stdout, stderr = self.client.exec_command(command)
            if feed_password:
                stdin.write(self.ssh_password + "\n")
                stdin.flush()

            print(f'Debugging: execute command: ' + command)
            # Read and print the output
            output = stdout.read().decode('utf-8')
            print(f'Debugging: execute command response: ' + output)

            # Read and print any errors
            errors = stderr.read().decode('utf-8')
            if errors:
                print(f'Debugging: execute command errors: ' + errors)

            # return {'out': stdout.readlines(),
            #         'err': stderr.readlines(),
            #         'retval': stdout.channel.recv_exit_status()}
        except Exception as e:
            print(f"Error executing command: {str(e)}")

        return output


# SSH connection details
ssh_host = "192.168.124.128"
ssh_username = "root"
ssh_password = "111111"


if __name__ == "__main__":
    ssh = SshUtil(ssh_host, ssh_username, ssh_password)
    ssh.execute_shell_command("pwd", sudo=False)
    del ssh








