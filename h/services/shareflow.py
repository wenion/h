import pytz
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin

from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from h.db.types import InvalidUUID
from h.models import (
    Shareflow,
    ShareflowMetadata,
    ShareflowImage,
    Group,
    GroupShareflowMetadata,
    User,
    UserShareflowMetadata,
)
from h.models_redis import (
    get_user_role_by_userid,
    UserEvent,
    UserEventRecord,
)
from h.services.exceptions import ValidationError
from h.services.group_list import GroupListService
from h.services.user import UserService
from h.services.trace import TraceService
from h.services.trace_model import address_events


class ShareflowService:
    def __init__(
        self,
        base_url: str,
        session: Session,
        group_list_service: GroupListService,
        user_service: UserService,
        trace_service: TraceService,
    ):
        self._base_url = base_url
        self._db = session
        self._group_list_service = group_list_service
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

    def is_valid_data_url(self, data_url: str) -> bool:
        pattern = re.compile(
            r'^data:([a-z]+/[a-z0-9\-\+\.]+);base64,[A-Za-z0-9+/=]+$',
            re.IGNORECASE
        )
        return bool(pattern.match(data_url))

    def create_shareflow_image(self, image) -> ShareflowImage:
        if self.is_valid_data_url(image):
            shareflow_image = ShareflowImage()
            shareflow_image.set_image(image)
            self._db.add(shareflow_image)
            return shareflow_image
        else:
            print("create_shareflow_image", image[:100])
            return None

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
                image_data = self._trace_service.get_image_data_by_pk(trace["image"])
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
                image_data = self._trace_service.get_image_data_by_pk(trace["image"])
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
                Shareflow.deleted.isnot(True),
                Shareflow.version == shareflow_metadata.version,
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

        image_url = None
        if shareflow.image_id:
            image_url = urljoin(
                self._base_url,
                "api/image/" + str(shareflow.image_id) + ".jpg"
            )

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
                'image': image_url,
            }
        )

        return model

    def present_shareflow_for_tad(
        self,
        shareflow: Shareflow,
        user_event: dict = None
    ):
        model = {}
        timestamp = int(shareflow.timestamp.timestamp() * 1000)
        event_source = user_event.event_source if user_event else ''
        interaction_context = (
            user_event.interaction_context
                if user_event else shareflow.description
        )
        x_path = user_event.x_path if user_event else ''
        session_id = user_event.session_id if user_event else ''
        task_name = user_event.task_name if user_event else ''
        title = user_event.title if user_event else shareflow.title
        text_content = (
            user_event.text_content if user_event else shareflow.description
        )

        model.update(
            {
                'id': shareflow.id,
                'index': shareflow.index,
                'metadata_id': shareflow.metadata_id,
                'pk': shareflow.pk,
                'type': shareflow.type,
                'custom': shareflow.title,
                'label': shareflow.description,
                'tagName': shareflow.tag_name,
                'textContent': text_content,
                'interactionContext': interaction_context,
                'xpath': x_path,
                'eventSource': event_source,
                'width': shareflow.width,
                'height': shareflow.height,
                'clientX': shareflow.client_x,
                'clientY': shareflow.client_y,
                'screenCapture': False,
                'url': shareflow.url,
                'tabId': '',
                'windowId': '',
                'timestamp': timestamp,
                'image': '',
                'userid': '',
                'title': title,
                'region': '',
                'sessionId': session_id,
                'taskName': task_name,
                'ipAddress': '',
                'groups': '',
                'client_id': '',
            }
        )

        return model

    def get_shareflow_metadata_by_session_id(self, session_id):
        query = self._db.query(ShareflowMetadata).filter(
            ShareflowMetadata.session_id == session_id
        )

        return query.one_or_none()

    def get_shareflow_metadata_by_id(self, id_: str) -> Optional[ShareflowMetadata]:
        try:
            return self._db.get(ShareflowMetadata, id_)
        except InvalidUUID:
            return None

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

    def present_shareflow_meta_for_user(
        self,
        shareflow_metadata: ShareflowMetadata,
        current_user: User
    ):
        shareflow_metadata_dict = self.shareflow_metadata_dict(
            shareflow_metadata,
            current_user
        )

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
            "extra": shareflow_metadata.extra,
            "groupid": shareflow_metadata.groupid,
            "groups": shareflow_metadata_dict["groups"],
            "shared": shareflow_metadata.shared,
            "score": shareflow_metadata_dict["score"],
            "scores": shareflow_metadata_dict["scores"],
        }

        return model

    def shareflow_metadata_dict(
        self,
        shareflow_metadata: ShareflowMetadata,
        current_user: User
    ):
        model = {}

        userid = shareflow_metadata.user.userid
        user_role = get_user_role_by_userid(userid)

        request_groups = None
        if userid != current_user.userid:
            request_groups = self._group_list_service.request_groups(user=current_user)

        groups_list = self.get_groups_from_shareflow_metadata(
            shareflow_metadata,
            request_groups
        )
        groups = [group.pubid for group in groups_list]

        score = self.get_score_from_user_shareflow_metadata(shareflow_metadata, current_user)
        scores = self.get_total_score(shareflow_metadata)

        model.update(
            {
                "id": shareflow_metadata.id, # id: set as pk
                "created": self.normalize_to_iso_utc_z(shareflow_metadata.created),
                "updated": self.normalize_to_iso_utc_z(shareflow_metadata.updated),
                "startstamp": self.normalize_to_iso_utc_z(shareflow_metadata.updated),
                "endstamp": self.normalize_to_iso_utc_z(shareflow_metadata.endstamp),
                "session_id": shareflow_metadata.session_id,
                "task_name": shareflow_metadata.task_name,
                "description": shareflow_metadata.description,
                "pk": shareflow_metadata.pk,
                "version": shareflow_metadata.version,
                "role": user_role.teaching_role,
                "extra": shareflow_metadata.extra,
                "userid": userid,
                "groupid": shareflow_metadata.groupid,
                "groups": groups,
                "shared": shareflow_metadata.shared,
                "score": score,
                "scores": scores,
            }
        )

        return model

    def get_shareflow_image_by_id(self, id_: str):
        try:
            return self._db.get(ShareflowImage, id_)
        except:
            return None

    def get_shareflow_metadata_list_by_user(
        self,
        user: User,
        shared: bool = True
    ) -> List[ShareflowMetadata]:
        group_query = []

        if shared:
            groups = self._group_list_service.request_groups(user=user)
            group_shareflow_metadata_list = self.get_shareflow_metadata_from_groups(groups)
            group_query = [shareflow_metadata.id for shareflow_metadata in group_shareflow_metadata_list]

        combined_list = (
            self._db.query(ShareflowMetadata)
            .filter(
                or_(
                    ShareflowMetadata.user == user,
                    ShareflowMetadata.id.in_(group_query)
                )
            )
            .distinct()
            .all()
        )
        return combined_list

    def get_shareflow_metadata_from_groups(self, groups: list[Group]) -> list[ShareflowMetadata]:
        return (
            self._db.query(ShareflowMetadata)
            .join(GroupShareflowMetadata, GroupShareflowMetadata.shareflow_metadata_id == ShareflowMetadata.id)
            .filter(GroupShareflowMetadata.group_id.in_([group.id for group in groups]))
            .distinct()
            .all()
        )

    def get_groups_from_shareflow_metadata(
        self,
        shareflow_metadata: ShareflowMetadata,
        groups: list[Group] | None
    ) -> list[Group]:
        query = (
            self._db.query(Group)
            .join(GroupShareflowMetadata, Group.id == GroupShareflowMetadata.group_id)
            .filter(GroupShareflowMetadata.shareflow_metadata_id == shareflow_metadata.id)
        )

        if groups is not None:
            group_ids = [g.id for g in groups]
            query = query.filter(Group.id.in_(group_ids))

        return query.distinct().all()

    def get_groups_from_shareflow_metadata_id(self, shareflow_metadata_id) -> list[Group]:
        return (
            self._db.query(Group)
            .join(GroupShareflowMetadata, Group.id == GroupShareflowMetadata.group_id)
            .filter(GroupShareflowMetadata.shareflow_metadata_id == shareflow_metadata_id)
            .distinct()
            .all()
        )

    def delete_shareflow_metadata(self, shareflow_metadata):
        self._db.delete(shareflow_metadata)

    def add_group_to_shareflow_metadata(self, shareflow_metadata: ShareflowMetadata, group: Group):
        shareflow_metadata_id = shareflow_metadata.id
        group_id = group.id

        existing = self._db.query(GroupShareflowMetadata).filter(
            GroupShareflowMetadata.group_id == group_id,
            GroupShareflowMetadata.shareflow_metadata_id == shareflow_metadata_id,
        ).one_or_none()

        if existing:
            return existing

        group_shareflow_metadata = GroupShareflowMetadata(
            group_id=group_id,
            shareflow_metadata_id=shareflow_metadata_id
        )
        self._db.add(group_shareflow_metadata)
        return group_shareflow_metadata


    def remove_group_to_shareflow_metadata(self, shareflow_metadata, group):
        shareflow_metadata_id = shareflow_metadata.id
        group_id = group.id

        association = self._db.query(GroupShareflowMetadata).filter(
            GroupShareflowMetadata.group_id == group_id,
            GroupShareflowMetadata.shareflow_metadata_id == shareflow_metadata_id,
        ).one_or_none()

        if association:
            self._db.delete(association)
            return True  # Indicate successful removal

        return False  # Association didn't exist

    def add_user_shareflow_metadata(self, shareflow_metadata: ShareflowMetadata, user: User, data = 1):
        shareflow_metadata_id = shareflow_metadata.id
        user_id = user.id
        score = data

        existing = self._db.query(UserShareflowMetadata).filter(
            UserShareflowMetadata.user_id == user_id,
            UserShareflowMetadata.shareflow_metadata_id == shareflow_metadata_id,
        ).one_or_none()

        if existing:
            existing.score = score
            return existing

        user_shareflow_metadata = UserShareflowMetadata(
            user_id=user_id,
            shareflow_metadata_id=shareflow_metadata_id,
            score=score
        )
        self._db.add(user_shareflow_metadata)
        return user_shareflow_metadata

    def remove_user_shareflow_metadata(self, shareflow_metadata, user):
        shareflow_metadata_id = shareflow_metadata.id
        user_id = user.id

        association = self._db.query(UserShareflowMetadata).filter(
            UserShareflowMetadata.user_id == user_id,
            UserShareflowMetadata.shareflow_metadata_id == shareflow_metadata_id,
        ).one_or_none()

        if association:
            self._db.delete(association)
            return True  # Indicate successful removal

        return False  # Association didn't exist

    def get_score_from_user_shareflow_metadata(self, shareflow_metadata, user):
        shareflow_metadata_id = shareflow_metadata.id
        user_id = user.id

        existing = self._db.query(UserShareflowMetadata).filter(
            UserShareflowMetadata.shareflow_metadata_id == shareflow_metadata_id,
            UserShareflowMetadata.user_id == user_id,
        ).one_or_none()

        if existing:
            return existing.score
        else:
            return 0

    def get_total_score(self, shareflow_metadata):
        shareflow_metadata_id = shareflow_metadata.id
        total_score = (
            self._db.query(func.sum(UserShareflowMetadata.score))
            .filter(UserShareflowMetadata.shareflow_metadata_id == shareflow_metadata_id)
            .scalar()
        )
        return total_score or 0  # Returns 0 if no matching records are found

def shareflow_service_factory(_context, request):
    return ShareflowService(
        request.route_url("index"),
        request.db,
        request.find_service(name="group_list"),
        request.find_service(name="user"),
        request.find_service(name="trace"),
    )
