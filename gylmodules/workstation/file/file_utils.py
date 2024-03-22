import os.path
import stat

import paramiko


# SSH connection details
ssh_host = "192.168.124.128"
ssh_username = "root"
ssh_password = "111111"

# Specify the remote directory path (optional, defaults to the home directory)
remote_path = '/home/yanliang/file-manager'


# class File:
#     name: str
#     type: str
#     size: int
#     path:  str
#     children: []


class FileUtil:

    """构造函数"""
    def __init__(self, host: str, username: str, password: str):
        self.ssh_host = host
        self.ssh_username = username
        self.ssh_password = password

        self.file_list = []
        self.space = ""

        # Create an SSH client
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the SSH server
        try:
            self.ssh.connect(ssh_host, 22, username=ssh_username, password=ssh_password)
        except Exception as e:
            log.debug(f"Unable to establish SSH connection: {str(e)}")

    """Close the SSH connection"""
    def __del__(self):
        if self.ssh is not None:
            self.ssh.close()
            self.ssh = None
        log.debug("Close the SSH connection!")

    def list_remote_directory(self, path='.'):
        try:
            # Open an SFTP session
            sftp = self.ssh.open_sftp()

            self.file_list = []
            self.space = ""

            # List the contents of the remote directory recursively
            dirtree = self.list_remote_directory_recursive(sftp, path)

            # Close the SFTP session
            sftp.close()

        except Exception as e:
            print(f"Error: {e}")

        return dirtree

    def list_remote_directory_recursive(self, sftp,  path='.') -> File:
        dirtree = File(name=path.split("/")[-1], path=path, file_type="directory")

        files = sftp.listdir_attr(path)
        for file in files:
            full_path = f"{path}/{file.filename}"

            # 目录
            if stat.S_ISDIR(file.st_mode):
                print(str(self.space) + "|____" + file.filename)
                self.space = self.space + "|    "
                children = self.list_remote_directory_recursive(sftp, full_path)
                dirtree.children.append(children)
                self.space = self.space[:-5]
            # 文件
            else:
                dirtree.children.append(File(name=file.filename, path=full_path, file_type="file", size=file.st_atime))
                print(str(self.space) + "|____" + file.filename + " " + str(file.st_size) + " bytes")
        return dirtree

    """
    计算文件大小并将其动态转换为K、M、GB等。
    calculate file size and dynamically convert it to K, M, GB, etc.
    :param file_path:
    :param total_size: the size of a dir
    :return: file size with format
    """
    @staticmethod
    def bytes_conversion(file_path, total_size=-1):
        number = 0
        if total_size == -1:
            number = os.path.getsize(file_path)
        else:
            number = total_size
        symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
        prefix = dict()
        for a, s in enumerate(symbols):
            prefix[s] = 1 << (a + 1) * 10
        for s in reversed(symbols):
            if int(number) >= prefix[s]:
                value = float(number) / prefix[s]
                return '%.2f%s' % (value, s)
        return "%sB" % number


if __name__ == "__main__":
    file_util = FileUtil(ssh_host, ssh_username, ssh_password)
    file_util.list_remote_directory(remote_path)
