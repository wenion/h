import datetime
import os
import shutil
from redis_om.model import NotFoundError

from h import util
from h.models_redis import FileMeta


MAPPING_TYPE = {
    'application/pdf' : 'pdf',
    'text/html': 'html',
    'text/plain': 'txt',
    'text/csv': 'csv',
    'application/msword': 'doc',
}

class FileManagementService:
    """A service for manipulating file (user event record)."""

    def __init__(self, request):
        """
        Create a new record item service.
        """
        self.request = request

    @staticmethod
    def file_meta_dict(filemeta):
        return {
            "id": filemeta.pk,
            "filename": filemeta.filename,
            "fileId": filemeta.file_id,
            "createStamp": filemeta.create_stamp,
            "updateStamp": filemeta.update_stamp,
            "fileType": filemeta.file_type,
            "filePath": filemeta.file_path,
            "url": filemeta.url,
            "userid": filemeta.userid,
            "permission": filemeta.access_permissions,
        }

    @staticmethod
    def _create_dir_if_not_exist(dir, options):
        result = FileMeta.find(
            (FileMeta.file_path == dir) &
            (FileMeta.file_type == 'directory') &
            (FileMeta.deleted == 0)
        ).all()

        if len(result):
            return result[0]
        else:
            now = datetime.datetime.now().timestamp()
            return FileManagementService.create_file_meta({
                "filename": dir,
                "create_stamp": now,
                "file_path": dir,
                "link": options["link"],
                "userid": options["userid"],
                "access_permissions": options["access_permissions"],
            })

    @staticmethod
    def mk_v_dir(dir, options):
        dir = os.path.abspath(os.path.join("/", dir))
        dir_list = dir.split('/')

        path = '/'
        for sub in dir_list:
            path = os.path.join(path, sub)
            FileManagementService._create_dir_if_not_exist(path, options)
        return dir

    @staticmethod
    def check_v_dir_exist(path):
        result = FileMeta.find(
            (FileMeta.file_path == path) &
            (FileMeta.file_type == 'directory') &
            (FileMeta.deleted == 0)
        ).all()
        return result[0] if len(result) else None

    @staticmethod
    def _get_v_files(path):
        result = FileMeta.find(
            (FileMeta.file_path == path) &
            (FileMeta.deleted == 0)
        ).all()
        return result
    
    @staticmethod    
    def _get_root():
        return FileManagementService._create_dir_if_not_exist('/', {
            "link": "",
            "userid": "",
            "access_permissions": "public",
        })

    @staticmethod
    def _get_user_root(userid):
        root = FileManagementService._get_root().file_path
        username = util.user.split_user(userid)["username"]
        dir = os.path.join(root, username)
        return FileManagementService._create_dir_if_not_exist(dir, {
            "link": "",
            "userid": userid,
            "access_permissions": "private",
        })

    @staticmethod
    def get_user_files_list_by_dir(userid, dir = None):
        if not dir:
            dir = FileManagementService._get_user_root(userid).file_path

        result = FileManagementService._get_v_files(dir)

        files = []
        for i in result:
            if i:= FileManagementService.permission_check(userid, i):
                files.append(FileManagementService.file_meta_dict(i))
        return [ files, dir, ]

    # @staticmethod
    # def get_user_file_by_id(userid, pk_id):
    #     file = FileManagementService.get_file_by_id(pk_id)
    #     if filemeta:=FileManagementService.permission_check(userid, file):
    #         return filemeta
    #     return None

    @staticmethod
    def get_file_by_id(pk):
        """Return a file meta which isn't deleted"""
        try:
            file = FileMeta.get(pk)
        except NotFoundError:
            return None
        finally:
            if file.deleted:
                return None
            return file

    @staticmethod
    def save_file(src_file, dest, data):
        try:
            src_file.seek(0)
            with open(dest, "wb") as output_file:
                shutil.copyfileobj(src_file, output_file)
        except Exception as e:
            return None
        else:
            return FileManagementService.create_file_meta(data)

    @staticmethod
    def create_file_meta(data):
        file_meta = FileMeta(
            filename = data["filename"],
            file_id = data.get("file_id", ""),
            create_stamp = data["create_stamp"],
            update_stamp = data["create_stamp"],
            file_type = data.get("file_type", "directory"),
            file_path = data["file_path"],
            link = data.get("link", ""),
            userid = data["userid"],
            access_permissions = data.get("access_permissions", "private"),
            url = data.get("url", ""),
            deleted = 0,
        )
        file_meta.save()
        return file_meta

    @staticmethod
    def update_file_meta(pk, data, userid):
        file_meta = FileManagementService.get_file_by_id(pk)
        if file_meta and file_meta.userid == userid:
            if "filename" in data:
                file_meta.filename = data["filename"]
            if "update_stamp" in data:
                file_meta.update_stamp = data["create_stamp"]
            if "file_path" in data:
                file_meta.file_path = data["file_path"]
            if "access_permissions" in data:
                file_meta.access_permissions = data["access_permissions"]
            if "deleted" in data:
                file_meta.deleted = data["deleted"]
            file_meta.save()
            return file_meta
        else:
            return None
    
    @staticmethod
    def delete_file_meta(pk, userid):
        if FileManagementService.update_file_meta(pk, {"deleted": 1}, userid):
            return True
        else:
            return False

    @staticmethod
    def permission_check(userid, file_meta: FileMeta):
        if not file_meta:
            return None
        if file_meta.access_permissions != "private":
            return file_meta
        else:
            if file_meta.userid == userid:
                return file_meta
            else:
                return None

    @staticmethod
    def check_accpectable_file_type(file_type):
        return MAPPING_TYPE.get(file_type, None)

def file_management_factory(_context, request):
    """Return a RecordItemService instance for the request."""
    return FileManagementService(request)
