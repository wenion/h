import colander
from deform.widget import TextAreaWidget, TextInputWidget, SelectWidget

import h.i18n
from h.models.organisation_event import OrganisationEvent
from h.schemas import validators
from h.schemas.base import CSRFSchema
from h.schemas.forms.widgets import DateInputWidget

_ = h.i18n.TranslationString


@colander.deferred
def organisation_event_group_select_widget(_node, kwargs):
    orgs = kwargs["group"]
    org_labels = []
    org_pubids = []
    for org in orgs.values():
        org_labels.append(f"{org.name}")
        org_pubids.append(org.pubid)

    # `zip` returns an iterator. The `SelectWidget` constructor requires an
    # actual list.
    return SelectWidget(values=list(zip(org_pubids, org_labels)))


@colander.deferred
def organisation_event_campus_select_widget(_node, kwargs):
    return SelectWidget(values=kwargs["campus"])


class OrganisationEventSchema(CSRFSchema):
    date = colander.SchemaNode(
        colander.Date(),
        title=_("Date (dd/mm/yyyy)"),
        widget=DateInputWidget(),
    )

    groupid = colander.SchemaNode(
        colander.String(),
        title=_("Group"),
        widget=organisation_event_group_select_widget
    )

    event_name = colander.SchemaNode(
        colander.String(),
        title=_("Event Name"),
        validator=validators.Length(
            OrganisationEvent.NAME_MIN_CHARS, OrganisationEvent.NAME_MAX_CHARS
        ),
        widget=TextInputWidget(max_length=OrganisationEvent.NAME_MAX_CHARS),
    )

    campus = colander.SchemaNode(
        colander.String(),
        title=_("Campus"),
        widget=organisation_event_campus_select_widget
    )

    text = colander.SchemaNode(
        colander.String(),
        title=_("Message"),
        hint=_(
            "The content is in Markdown format"
        ),
        widget=TextAreaWidget(rows=5),
        missing=None,
    )
