import pysftp as pysftp

from gylmodules.workstation import ws_config
from gylmodules.workstation.file.file_utils import FileUtil


def is_supported(filename: str):
    """
    判断当前文件后缀是否支持处理
    """
    if filename is None or not filename.__contains__('.'):
        raise Exception('filename: ' + filename + 'exception')
    return filename.rsplit('.', 1)[1].lower() in ws_config.FILE_ALLOWED_EXTENSIONS


def sftp_upload(local_path, remote_path):
    """
    将本地文件通过 sftp 上传到远程服务器
    :return:
    """
    with pysftp.Connection(ws_config.FILE_SFTP_HOST,
                           port=ws_config.FILE_SFTP_PORT,
                           username=ws_config.FILE_SFTP_USERNAME,
                           password=ws_config.FILE_SFTP_PASSWORD) as sftp:
        sftp.put(local_path, remote_path)
        sftp.close()


def sftp_download(local_path, remote_path):
    """
    通过 sftp 从远程服务器下载文件到本地
    :return:
    """
    try:
        with pysftp.Connection(ws_config.FILE_SFTP_HOST,
                               port=ws_config.FILE_SFTP_PORT,
                               username=ws_config.FILE_SFTP_USERNAME,
                               password=ws_config.FILE_SFTP_PASSWORD) as sftp:
            # Download the file
            if sftp.exists(remote_path):
                # Download the file
                sftp.get(remote_path, local_path)
                print(f"File downloaded successfully: {remote_path}")
            else:
                print(f"Remote file does not exist: {remote_path}")
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
    sftp.close()


def query_file_list():
    file_util = FileUtil(ws_config.FILE_SSH_HOST, ws_config.FILE_SSH_USERNAME, ws_config.FILE_SSH_PASSWORD)
    dirtree = file_util.list_remote_directory(ws_config.FILE_SFTP_REMOTE_FILES_PATH)
    return dirtree


def render_tree(node):
    """
    Recursively render the file/directory tree.
    """
    if node.type == 'file':
        return f"<p><a href=\"{{ url_for(\'download\', file_path=\' {node.path}\') }} \">{node.name}</a></p>"
        # return f"<li>{node.name}</li>"

    children = ''.join(render_tree(child) for child in node.children)
    # return f"<p>Uploaded File: <a href=\"/download/{{ node.path }} \">{{ node.name }}</a></p>"
    return f"<li>{node.name}<ul>{children}</ul></li>"
