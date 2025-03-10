from datetime import datetime
import pytz

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from h.db.types import InvalidUUID
from h.models import Shareflow, ShareflowMetadata, ShareflowImage, User
from h.services.exceptions import ValidationError
from h.services.user import UserService


class ShareflowService:
    def __init__(
        self,
        session: Session,
        user_service: UserService,
    ):
        self._db = session
        self._user_service = user_service

    def format_shareflow_metadata(self, data: dict, shareflow_metadata: ShareflowMetadata = None):
        data.pop("target_url", None)
        data.pop("completed", None)
        data.pop("sessionId", None)
        data.pop("taskName", None)
        data.pop("role", None)
        data.pop("timestamp", None)
        data.pop("id", None)

        tz = data.pop("timezone", "Australia/Sydney")
        local_tz = pytz.timezone(tz)

        startstamp = data.pop("startstamp", None)
        if startstamp:
            start_datetime = startstamp / 1000
            data["startstamp"] = datetime.fromtimestamp(start_datetime, local_tz).astimezone(pytz.utc)

        endstamp = data.pop("endstamp", None)
        if endstamp:
            end_datetime = endstamp / 1000
            data["endstamp"] = datetime.fromtimestamp(end_datetime, local_tz).astimezone(pytz.utc)

        if not shareflow_metadata:
            backdate = data.pop("backdate", 0)
            data["backdate"] = backdate

            isShared = data.pop("shared", False)
            data["shared"] = isShared

            userid = data.pop("userid")
            user = self._user_service.fetch(userid)
            data["user"] = user

            groupid = data.pop("group", "__world__")
            data["groupid"] = groupid
        return data

    def create_shareflow_metadata(self, data: dict):
        data = self.format_shareflow_metadata(data)
        shareflow_meta = ShareflowMetadata(**data)
        self._db.add(shareflow_meta)
        return shareflow_meta

    def create_shareflow(self, data: dict, shareflow_metadata: ShareflowMetadata, image, user_id):
        data.pop("id", None)
        data.pop("index", None)
        data["metadata_ref"] = shareflow_metadata
        data["tag_name"] = data.get("tagName")
        data["client_x"] = data.get("clientX")
        data["client_y"] = data.get("clientY")

        data.pop("tagName", None)
        data.pop("clientX", None)
        data.pop("clientY", None)
        data.pop("state", None)
        data["image"] = None
        if image:
            shareflow_image = ShareflowImage()
            shareflow_image.set_image(image)
            self._db.add(shareflow_image)
            data["image"] = shareflow_image

        tz = data.pop("timezone", "Australia/Sydney")
        local_tz = pytz.timezone(tz)
        timestamp = data.pop("timestamp")
        timestamp_datetime = timestamp / 1000
        data["timestamp"] = datetime.fromtimestamp(timestamp_datetime, local_tz).astimezone(pytz.utc)

        data["user_id"] = user_id

        shareflow = Shareflow(**data)
        self._db.add(shareflow)
        return shareflow
    
    def update_shareflow(self, shareflow, **kwargs):
        for key, value in kwargs.items():
            try:
                setattr(shareflow, key, value)
            except ValueError as err:
                raise ValidationError(err) from err

        try:
            self._db.flush()
        except SQLAlchemyError as err:
            raise

        return shareflow
    
    def delete_shareflow(self, shareflow):
        try:
            setattr(shareflow, "deleted", True)
        except ValueError as err:
            raise ValidationError(err) from err
        try:
            self._db.flush()
        except SQLAlchemyError as err:
            raise

        return shareflow
    
    def get_shareflows_by_session_id(self, id: str):
        shareflow_metadata = self.read_shareflow_metadata_by_session_id(id)
        if shareflow_metadata:
            shareflows = shareflow_metadata.shareflows
            # order by
            # return [self.present_shareflow(shareflow) for shareflow in shareflows]
            return [self.present_shareflow(shareflow) for shareflow in shareflows if not getattr(shareflow, 'deleted', False)]
        else:
            raise InvalidUUID

    def present_shareflow(self, shareflow: Shareflow):
        model = {}
        timestamp = int(shareflow.timestamp.timestamp() * 1000) if shareflow.timestamp else None

        model.update(
            {
                'id': shareflow.id,
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

    def read_shareflow_by_id(self, id_: str):
        try:
            return self._db.get(Shareflow, id_)
        except InvalidUUID:
            return None
        
    def read_shareflow_metadata_by_session_id(self, session_id):
        query = self._db.query(ShareflowMetadata).filter(
            ShareflowMetadata.session_id == session_id
        )
        
        return query.one_or_none()

    def present(self, shareflow_metadata: ShareflowMetadata):
        model = {}

        startstamp = int(shareflow_metadata.startstamp.timestamp() * 1000) if shareflow_metadata.startstamp else None
        endstamp = int(shareflow_metadata.endstamp.timestamp() * 1000) if shareflow_metadata.endstamp else None

        model.update(
            {
                "id": shareflow_metadata.pk, # id: set as pk
                "description": shareflow_metadata.description,
                "pk": shareflow_metadata.pk,
                "role": shareflow_metadata.description,
                "timestamp": startstamp,
                "userid": shareflow_metadata.user.userid,
                "taskName": shareflow_metadata.task_name,
                "sessionId": shareflow_metadata.session_id,
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

    def json_shareflow_metadata_search_query(self, userid, shared = True):
        all = self.shareflow_metadata_search_query(userid, shared)
        return [self.present(shareflow_metadata) for shareflow_metadata in all]

    def shareflow_metadata_search_query(self, userid, shared = True):
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

    def update_shareflow_metadata(self, data: dict, shareflow_metadata: ShareflowMetadata):
        data = self.format_shareflow_metadata(data, shareflow_metadata)
        return self.updat_shareflow_metadata_by_id(shareflow_metadata, **data)

    def updat_shareflow_metadata_by_id(self, shareflow_metadata, **kwargs):
        for key, value in kwargs.items():
            try:
                setattr(shareflow_metadata, key, value)
            except ValueError as err:
                raise ValidationError(err) from err

        try:
            self._db.flush()
        except SQLAlchemyError as err:
            raise

        return shareflow_metadata
    
    def delete_shareflow_metadata(self, shareflow_metadata):
        self._db.delete(shareflow_metadata)

def shareflow_service_factory(_context, request):
    return ShareflowService(
        request.db,
        request.find_service(name="user")
    )
