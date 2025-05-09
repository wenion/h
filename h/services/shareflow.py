from datetime import datetime
import pytz
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from h.db.types import InvalidUUID
from h.models import User, Group, Shareflow, ShareflowMetadata, ShareflowImage
from h.models_redis import get_user_role_by_userid, UserEventRecord
from h.services.exceptions import ValidationError
from h.services.user import UserService
from h.services.trace import TraceService
from h.services.trace_model import address_events


class ShareflowService:
    def __init__(
        self,
        session: Session,
        user_service: UserService,
        trace_service: TraceService,
    ):
        self._db = session
        self._user_service = user_service
        self._trace_service = trace_service

    def create_shareflow_metadata_from_record(
        self,
        data: UserEventRecord,
        userid: str,
        startstamp: Optional[datetime] = None,
        endstamp: Optional[datetime] = None,
        group: Optional[Group] = None
    ):
        model = {
            'pk': data.pk,
            # withdraw the frontend's sessionId
            'session_id': data.pk,
            'task_name': data.task_name,
            'description': data.description,
            'backdate': data.backdate,
        }
        user = self._user_service.fetch(userid)
        model['user'] = user
        if startstamp:
            model['startstamp'] = startstamp
        if endstamp:
            model['endstamp'] = endstamp
        if group:
            model['group'] = group

        shareflow_meta = ShareflowMetadata(**model)
        self._db.add(shareflow_meta)
        return shareflow_meta

    def create_shareflow_image(self, image) -> ShareflowImage:
        shareflow_image = ShareflowImage()
        shareflow_image.set_image(image)
        self._db.add(shareflow_image)
        return shareflow_image

    def generate_shareflows(
        self,
        shareflow_metadata: ShareflowMetadata,
        version: int,
    ) -> List[Shareflow]:
        session_id = shareflow_metadata.session_id
        user = shareflow_metadata.user

        all = self._trace_service.get_traces_by_session_id_sorted(session_id)
        traces = address_events(all)
        for index, trace in enumerate(traces):
            shareflow_image = None
            if trace.get('image', None):
                image_data = self._trace_service.get_image_data_by_pk(trace["pk"])
                shareflow_image = self.create_shareflow_image(image_data)

            requirements = [
                'index', 'pk', 'type', 'title', 'description', 'timestamp',
                'tag_name', 'width', 'height', 'client_x', 'client_y', 'url',
                'version', 'metadata_id', 'image_id', 'user_id',
            ]

            filtered_data = {key: trace[key] for key in requirements if key in trace}

            self.create_shareflow_from_cache(
                filtered_data,
                user,
                shareflow_metadata,
                index + 1, # start from 1
                version,
                shareflow_image,
            )

    def regenerate_shareflows(
        self,
        shareflow_metadata: ShareflowMetadata,
    ):
        session_id = shareflow_metadata.session_id
        user = shareflow_metadata.user

        self.delete_shareflows(shareflow_metadata)

        user = shareflow_metadata.user
        shareflow_metadata.version = shareflow_metadata.version + 1

        all = self._trace_service.get_traces_by_session_id_sorted(session_id)
        traces = address_events(all)
        for index, trace in enumerate(traces):
            shareflow_image = None
            if trace.get('image', None):
                image_data = self._trace_service.get_image_data_by_pk(trace["pk"])
                shareflow_image = self.create_shareflow_image(image_data)

            requirements = [
                'index', 'pk', 'type', 'title', 'description', 'timestamp',
                'tag_name', 'width', 'height', 'client_x', 'client_y', 'url',
                'version', 'metadata_id', 'image_id', 'user_id',
            ]

            filtered_data = {key: trace[key] for key in requirements if key in trace}

            self.create_shareflow_from_cache(
                filtered_data,
                user,
                shareflow_metadata,
                index + 1, # start from 1
                shareflow_metadata.version,
                shareflow_image,
            )

    def create_shareflow_from_cache(
        self,
        data,
        user: User,
        shareflow_metadata: ShareflowMetadata,
        index: Optional[int],
        version: Optional[int],
        shareflow_image: Optional[ShareflowImage]
    ) -> Shareflow:
        data["user"] = user
        data["metadata_ref"] = shareflow_metadata
        if index:
            data['index'] = index
        if version:
            data['version'] = version
        if shareflow_image:
            data["image"] = shareflow_image

        shareflow = Shareflow(**data)
        self._db.add(shareflow)
        return shareflow

    def get_shareflow_by_id(self, id: str) -> Shareflow:
        shareflow = (
            self._db.query(Shareflow)
            .filter(
                Shareflow.id == id,
                Shareflow.deleted.isnot(True)
            )
            .one_or_none()
        )
        return shareflow

    def delete_shareflow(self, shareflow: Shareflow):
        try:
            setattr(shareflow, "deleted", True)
        except ValueError as err:
            raise ValidationError(err) from err
        try:
            self._db.flush()
        except SQLAlchemyError as err:
            raise

        return shareflow

    def get_shareflows(self, shareflow_metadata: ShareflowMetadata):
        shareflows = (
            self._db.query(Shareflow)
            .filter(
                Shareflow.metadata_ref == shareflow_metadata,
                Shareflow.deleted.isnot(True)
            )
            .order_by(Shareflow.index, Shareflow.timestamp)
            .all()
        )
        return shareflows

    def delete_shareflows(self, shareflow_metadata: ShareflowMetadata):
        (
            self._db.query(Shareflow)
            .filter(Shareflow.metadata_ref == shareflow_metadata)
            .update({Shareflow.deleted: True}, synchronize_session="fetch")
        )

    def present_shareflow_for_user(self, shareflow: Shareflow):
        model = {}
        timestamp = int(shareflow.timestamp.timestamp() * 1000)

        model.update(
            {
                'id': shareflow.id,
                'index': shareflow.index,
                'metadata_id': shareflow.metadata_id,
                'pk': shareflow.pk,
                'type': shareflow.type,
                'title': shareflow.title,
                'description': shareflow.description,
                'tagName': shareflow.tag_name,
                'timestamp': timestamp,
                'width': shareflow.width,
                'height': shareflow.height,
                'clientX': shareflow.client_x,
                'clientY': shareflow.client_y,
                'url': shareflow.url,
                'image': shareflow.image_id,
            }
        )

        return model

    def get_shareflow_metadata_by_session_id(self, session_id):
        query = self._db.query(ShareflowMetadata).filter(
            ShareflowMetadata.session_id == session_id
        )

        return query.one_or_none()

    @staticmethod
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

    def present_shareflow_meta_for_user(self, shareflow_metadata: ShareflowMetadata):
        shareflow_metadata_dict = self.shareflow_metadata_dict(shareflow_metadata)

        model =  {
            "id": shareflow_metadata.pk, # id: set as pk
            "description": shareflow_metadata.description,
            "pk": shareflow_metadata.pk,
            "role": shareflow_metadata_dict["role"],
            "timestamp": shareflow_metadata_dict["startstamp"],
            "userid": shareflow_metadata_dict["userid"],
            "taskName": shareflow_metadata.task_name,
            "sessionId": shareflow_metadata.session_id,
            "version": shareflow_metadata.version,
            "groupid": shareflow_metadata.groupid,
            "shared": shareflow_metadata.shared,
        }

        return model

    def shareflow_metadata_dict(self, shareflow_metadata: ShareflowMetadata):
        model = {}

        userid = shareflow_metadata.user.userid
        user_role = get_user_role_by_userid(userid)
        model.update(
            {
                "id": shareflow_metadata.id, # id: set as pk
                "created": self.normalize_to_iso_utc_z(shareflow_metadata.created),
                "updated": self.normalize_to_iso_utc_z(shareflow_metadata.updated),
                "startstamp": self.normalize_to_iso_utc_z(shareflow_metadata.startstamp),
                "endstamp": self.normalize_to_iso_utc_z(shareflow_metadata.endstamp),
                "session_id": shareflow_metadata.session_id,
                "task_name": shareflow_metadata.task_name,
                "description": shareflow_metadata.description,
                "pk": shareflow_metadata.pk,
                "version": shareflow_metadata.version,
                "role": user_role.teaching_role,
                "userid": userid,
                "groupid": shareflow_metadata.groupid,
                "shared": shareflow_metadata.shared,
            }
        )

        return model

    def get_shareflow_image_by_id(self, id_: str):
        try:
            return self._db.get(ShareflowImage, id_)
        except:
            return None

    def get_shareflow_metadata_list(
        self,
        userid: str,
        shared: bool = True
    ) -> List[ShareflowMetadata]:
        if shared:
            query = self._db.query(ShareflowMetadata).filter(
                or_(
                    ShareflowMetadata.user.has(User.userid == userid),
                    ShareflowMetadata.shared.is_(shared)
                )
            )
        else:
            query = self._db.query(ShareflowMetadata).filter(
                ShareflowMetadata.user_id == userid
            )
        return query.all()

    def delete_shareflow_metadata(self, shareflow_metadata):
        self._db.delete(shareflow_metadata)

def shareflow_service_factory(_context, request):
    return ShareflowService(
        request.db,
        request.find_service(name="user"),
        request.find_service(name="trace")
    )
