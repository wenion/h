from datetime import datetime, timezone
from jinja2 import Markup
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config, view_defaults
from pyramid.renderers import render
from sqlalchemy import func
from deform import Form

from h import form, i18n, models, paginator
from h.models.organisation_event import OrganisationEvent
from h.models.organisation_event_push_log import OrganisationEventPushLog
from h.schemas.forms.admin.organisation_event import OrganisationEventSchema
from h.security import Permission

_ = i18n.TranslationString


@view_config(
    route_name="admin.organisation_event",
    request_method="GET",
    renderer="h:templates/admin/organisation_event.html.jinja2",
    permission=Permission.AdminPage.LOW_RISK,
)
@paginator.paginate_query
def index(_context, request):
    q_param = request.params.get("q")

    filter_terms = []
    if q_param:
        filter_terms.append(func.lower(OrganisationEvent.event_name).like(f"%{q_param.lower()}%"))

    return (
        request.db.query(OrganisationEvent)
        .filter(*filter_terms)
        .order_by(OrganisationEvent.date.desc())
    )


@view_defaults(
    route_name="admin.organisation_event_create",
    renderer="h:templates/admin/organisation_event_create.html.jinja2",
    permission=Permission.AdminPage.LOW_RISK,
)
class OrganisationEventCreateController:
    def __init__(self, request):
        self.request = request

        self.group_svc = request.find_service(name="group").filter_by_name().all()
        self.campus = request.find_service(name="campus_list").campus()

        self.group = {g.name: g for g in self.group_svc}
        self.schema = OrganisationEventSchema().bind(request=request, group=self.group, campus=self.campus)
        self.form = request.create_form(
            self.schema, buttons=(_("Create organisation event"),)
        )

    @view_config(request_method="GET")
    def get(self):
        return self._template_context()

    @view_config(request_method="POST")
    def post(self):
        def on_success(appstruct):
            date_str = appstruct["date"]
            groupid = appstruct["groupid"]
            event_name = appstruct["event_name"]
            campus = appstruct["campus"]
            text = appstruct["text"]
            date_datetime = datetime.strptime(date_str, '%d/%m/%Y').astimezone(timezone.utc)
            organization = OrganisationEvent(date=date_datetime, groupid=groupid, event_name=event_name, campus=campus, text=text)

            self.request.db.add(organization)
            self.request.session.flash(
                # pylint:disable=consider-using-f-string
                Markup(_("Created new organisation event {}".format(event_name))),
                "success",
            )

            return HTTPFound(location=self.request.route_url("admin.organisation_event"))

        return form.handle_form_submission(
            self.request,
            self.form,
            on_success=on_success,
            on_failure=self._template_context,
        )

    def _template_context(self):
        return {"form": self.form.render()}


@view_defaults(
    route_name="admin.organisation_event_edit",
    permission=Permission.AdminPage.LOW_RISK,
    renderer="h:templates/admin/organisation_event_edit.html.jinja2",
)
class OrganizationEditController:
    def __init__(self, context, request):
        self.organization = context.organisation_event
        self.request = request

        self.group_svc = request.find_service(name="group").filter_by_name().all()
        self.campus = request.find_service(name="campus_list").campus()
        selected_group = request.find_service(name="group").fetch_by_pubid(context.organisation_event.groupid)
        self.selected_group = (context.organisation_event.groupid, selected_group.name)

        self.group = {g.name: g for g in self.group_svc}
        self.schema = OrganisationEventSchema().bind(request=request, group=self.group, campus=self.campus)
        self.form = request.create_form(self.schema, buttons=(_("Save"),))
        self._update_appstruct()

    @view_config(request_method="GET")
    def read(self):
        return self._template_context()

    @view_config(request_method="POST", route_name="admin.organisation_event_delete")
    def delete(self):
        # Delete the organization.
        # Delete OrganisationEventPush
        push_logs = self.request.db.query(OrganisationEventPushLog).filter_by(organisation_event_id=self.organization.id)
        for log in push_logs:
            self.request.db.delete(log)

        self.request.db.delete(self.organization)
        self.request.session.flash(
            _(
                # pylint:disable=consider-using-f-string
                "Successfully deleted organization %s" % (self.organization.event_name),
                "success",
            )
        )
        return HTTPFound(location=self.request.route_path("admin.organisation_event"))

    @view_config(request_method="POST")
    def update(self):
        org = self.organization

        def on_success(appstruct):
            org.date = datetime.strptime(appstruct["date"], '%d/%m/%Y').astimezone(timezone.utc)
            org.event_name = appstruct["event_name"]
            org.groupid = appstruct["groupid"]
            org.campus = appstruct["campus"]
            org.text = appstruct["text"]

            self._update_appstruct()

            return self._template_context()

        return form.handle_form_submission(
            self.request,
            self.form,
            on_success=on_success,
            on_failure=self._template_context,
        )

    def _update_appstruct(self):
        org = self.organization
        self.form.set_appstruct(
            {"date": org.date.replace(tzinfo=timezone.utc).astimezone().strftime('%d/%m/%Y'), "event_name": org.event_name, "campus": org.campus, "groupid": self.selected_group, "text": org.text}
        )

    def _template_context(self):
        delete_url = None
        if not self.organization.is_default:
            delete_url = self.request.route_url(
                "admin.organisation_event_delete", pubid=self.organization.pubid
            )
        return {"form": self.form.render(), "delete_url": delete_url, "markdown": self.organization.text_rendered}
