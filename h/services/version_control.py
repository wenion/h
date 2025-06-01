import pytz
from datetime import datetime
from redis_om.model import NotFoundError

from h.models_redis import (
    VersionControlMeta,
    VersionControlNode
)

def normalize_to_iso_utc_z(value):
    """
    Convert a datetime or ISO 8601 string with '+00:00' to a 'Z'-suffixed ISO UTC string.

    Supports:
    - Python datetime.datetime (with tzinfo)
    - ISO 8601 strings with '+00:00'
    - SQLAlchemy DateTime columns (when passed actual datetime values)
    """
    # Case 1: datetime object
    if isinstance(value, datetime):
        # If naive datetime, assume UTC (or replace with local timezone if needed)
        if value.tzinfo is None:
            value = pytz.UTC.localize(value)
        else:
            value = value.astimezone(pytz.UTC)
        return value.isoformat().replace("+00:00", "Z")

    # Case 2: ISO 8601 string with +00:00
    if isinstance(value, str) and value.endswith("+00:00"):
        return value.replace("+00:00", "Z")

    # Case 3: Already a string with Z or unrecognized format
    return value


class VersionControlService:
    def __init__(self, request):
        self.request = request

    @staticmethod
    def get(ref):
        all = VersionControlMeta.find(
            VersionControlMeta.external_ref == ref
        ).all()

        if len(all):
            return all[0]
        else:
            return None

    @staticmethod
    def head(ref):
        meta = VersionControlService.get(ref)
        return VersionControlService.read(meta.pk) if meta else None

    @staticmethod
    def create(ref, data):
        meta = VersionControlService.get(ref)
        if meta:
            return meta

        version = 1
        node = VersionControlNode(
            data = data,
            external_ref = ref,
            version = version,
            prev = None
        )
        node.save()
        meta = VersionControlMeta(
            external_ref = ref,
            version = version,
            current = node.pk
        )
        meta.save()
        return meta
    
    @staticmethod
    def read(pk):
        try:
            meta = VersionControlMeta.get(pk)
        except NotFoundError:
            return None
        else:
            node = VersionControlNode.get(meta.current)
            return node

    @staticmethod
    def history(pk):
        all = []
        try:
            meta = VersionControlMeta.get(pk)
        except NotFoundError:
            return all
        else:
            current = meta.current
            try:
                node = VersionControlNode.get(current)
            except NotFoundError:
                return all
            while node and node.prev:
                all.append({
                    "version": node.version,
                    "title": "v" + str(node.version),
                    "created": normalize_to_iso_utc_z(node.created),
                })
                node = VersionControlNode.get(node.prev)

            all.append({
                "version": node.version,
                "title": "v" + str(node.version),
                "created": normalize_to_iso_utc_z(node.created),
            })
            return all

    @staticmethod
    def upgrade(pk, data):
        try:
            meta = VersionControlMeta.get(pk)
        except NotFoundError:
            return None
        else:
            version = meta.version
            current = meta.current
            ref = meta.external_ref

            node = VersionControlNode(
                data = data,
                external_ref = ref,
                version = version + 1,
                prev = current
            )
            node.save()
            
            meta.version = meta.version + 1
            meta.current = node.pk
            meta.save()
            return meta

    @staticmethod
    def downgrade(pk, version):
        try:
            meta = VersionControlMeta.get(pk)
        except NotFoundError:
            return None
        else:

            while meta.version > version:
                current = meta.current
                node = VersionControlNode.get(current)
                if node.prev:
                    meta.current = node.prev
                    meta.version = node.version - 1
                    VersionControlNode.delete(current)
                    meta.save()
                else:
                    break
            return meta
    
    @staticmethod
    def delete(pk):
        try:
            meta = VersionControlMeta.get(pk)
        except NotFoundError:
            return False
        else:
            while meta.version > 0:
                current = meta.current
                node = VersionControlNode.get(current)
                meta.current = node.prev
                meta.version = node.version - 1
                VersionControlNode.delete(current)
            
            VersionControlMeta.delete(pk)
            return True


def version_control_factory(_context, request):
    """Return a RecordItemService instance for the request."""
    return VersionControlService(request)
