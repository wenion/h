from unittest.mock import sentinel

import pytest
from _pytest.mark import param
from h_matchers import Any
from sqlalchemy import select

from h.models import Annotation
from h.services.bulk_annotation import (
    BadDateFilter,
    BadFieldSpec,
    BulkAnnotationService,
    date_match,
)


class TestDateMatch:
    @pytest.mark.parametrize(
        "spec,expected",
        (
            param({"gt": "2001-01-01"}, ["2"], id="gt"),
            param({"gte": "2001-01-01"}, ["1", "2"], id="gte"),
            param({"lt": "2001-01-01"}, ["0"], id="lt"),
            param({"lte": "2001-01-01"}, ["0", "1"], id="lte"),
            param({"eq": "2001-01-01"}, ["1"], id="eq"),
            param({"ne": "2001-01-01"}, ["0", "2"], id="ne"),
            param({"gt": "2000-01-01", "lt": "2002-01-01"}, ["1"], id="combo"),
        ),
    )
    def test_it(self, db_session, factories, spec, expected):
        factories.Annotation(text="0", created="2000-01-01")
        factories.Annotation(text="1", created="2001-01-01")
        factories.Annotation(text="2", created="2002-01-01")

        annotations = (
            db_session.execute(
                select(Annotation).where(date_match(Annotation.created, spec))
            )
            .scalars()
            .all()
        )

        assert [anno.text for anno in annotations] == Any.list.containing(
            expected
        ).only()

    @pytest.mark.parametrize(
        "bad_spec",
        (
            param({}, id="empty"),
            param({"bad_op": "2002-01-01"}, id="bad_op"),
        ),
    )
    def test_it_raises_for_bad_spec(self, bad_spec):
        with pytest.raises(BadDateFilter):
            date_match(sentinel.column, bad_spec)


class TestBulkAnnotationService:
    AUTHORITY = "my.authority"

    @pytest.mark.parametrize(
        "key,value,visible",
        (
            (None, None, True),
            ("shared", False, False),
            ("deleted", True, False),
            ("nipsad", True, False),
            ("moderated", True, False),
            ("updated", "2020-01-01", False),
            ("updated", "2020-01-02", True),
            ("updated", "2022-01-01", True),
            ("updated", "2022-01-02", False),
        ),
    )
    def test_it_with_single_annotation(self, svc, factories, key, value, visible):
        values = {
            "shared": True,
            "deleted": False,
            "nipsad": False,
            "moderated": False,
            "updated": "2021-01-01",
        }
        if key:
            values[key] = value

        viewer = factories.User(authority=self.AUTHORITY)
        author = factories.User(authority=self.AUTHORITY, nipsa=values["nipsad"])
        anno = factories.Annotation(
            userid=author.userid,
            group=factories.Group(members=[author, viewer]),
            shared=values["shared"],
            deleted=values["deleted"],
            updated=values["updated"],
        )
        if values["moderated"]:
            factories.AnnotationModeration(annotation=anno)

        annotations = svc.annotation_search(
            authority=self.AUTHORITY,
            audience={"username": [viewer.username]},
            updated={"gt": "2020-01-01", "lte": "2022-01-01"},
        )

        if visible:
            assert annotations == [anno]
        else:
            assert not annotations

    def test_it_with_more_complex_grouping(self, svc, factories):
        *viewers, author = factories.User.create_batch(3, authority=self.AUTHORITY)

        annotations = [
            factories.Annotation(
                userid=author.userid,
                group=factories.Group(members=group_members),
                shared=True,
                deleted=False,
            )
            for group_members in (
                # The first two annotations should match, because they are in
                # groups the viewers are in
                [author, viewers[0]],
                [author, viewers[1]],
                # This one is just noise and shouldn't match
                [author],
            )
        ]

        matched_annos = svc.annotation_search(
            authority=self.AUTHORITY,
            audience={"username": [viewer.username for viewer in viewers]},
            updated={"gt": "2020-01-01", "lte": "2099-01-01"},
        )

        # Only the first two annotations should match
        assert matched_annos == Any.list.containing(annotations[:2]).only()

    @pytest.mark.parametrize(
        "fields,expected",
        (
            (["author.username"], ("USERNAME",)),
            (["group.authority_provided_id"], ("AUTHORITY_PROVIDED_ID",)),
            (
                ["author.username", "group.authority_provided_id"],
                ("USERNAME", "AUTHORITY_PROVIDED_ID"),
            ),
            (
                ["group.authority_provided_id", "author.username"],
                ("AUTHORITY_PROVIDED_ID", "USERNAME"),
            ),
        ),
    )
    def test_it_with_fields(self, svc, factories, fields, expected):
        viewer = factories.User(authority=self.AUTHORITY)
        author = factories.User(authority=self.AUTHORITY, username="USERNAME")
        group = factories.Group(
            members=[viewer, author], authority_provided_id="AUTHORITY_PROVIDED_ID"
        )
        factories.Annotation(
            userid=author.userid,
            group=group,
            shared=True,
            deleted=False,
            updated="2021-01-01",
        )

        results = svc.annotation_search(
            authority=self.AUTHORITY,
            audience={"username": [viewer.username]},
            updated={"gt": "2020-01-01", "lte": "2099-01-01"},
            fields=fields,
        )

        assert results == [expected]

    @pytest.mark.parametrize(
        "bad_fields",
        (
            param([], id="empty_list"),
            param(["not.a_field"], id="bad_value"),
        ),
    )
    def test_it_with_bad_fields(self, svc, bad_fields):
        with pytest.raises(BadFieldSpec):
            svc.annotation_search(
                authority=self.AUTHORITY,
                audience={"username": ["something"]},
                updated={"gt": "2020-01-01", "lte": "2099-01-01"},
                fields=bad_fields,
            )

    @pytest.fixture
    def svc(self, db_session):
        return BulkAnnotationService(db_session)
