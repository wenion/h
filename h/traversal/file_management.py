from dataclasses import dataclass

from h.models_redis import FileMeta


@dataclass
class FileManagementContext:
    """Context for user_event views."""

    filemeta: FileMeta

    @property
    def id(self):
        return self.filemeta.pk

    @property
    def file_id(self):
        return self.filemeta.file_id

    @property
    def filename(self):
        return self.filemeta.filename


class FileRoot:
    """Root factory for routes whose context is an `FileManagementRoot`."""

    def __init__(self, request):
        self._file_management = request.find_service(name="file_management")

    def __getitem__(self, id):
        filemeta = self._file_management.get_file_by_id(id)

        if filemeta is None:
            raise KeyError()
        return FileManagementContext(filemeta)
