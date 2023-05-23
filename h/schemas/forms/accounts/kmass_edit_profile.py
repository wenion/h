import colander
import deform

from h import i18n
from h.schemas import validators
from h.schemas.base import CSRFSchema

_ = i18n.TranslationString


class KmassEditProfileSchema(CSRFSchema):
    faculty = colander.SchemaNode(
        colander.String(),
        title=_("Faculty"),
        widget=deform.widget.SelectWidget(
            values = (
                ("", "- Select -"),
                ('Information Technology', 'Information Technology'),
                ('Education', 'Education'),
                ('Law', 'Law'),
                ('Others', 'Others'),
            )
        )
    )

    teaching_role = colander.SchemaNode(
        colander.String(),
        title=_("Teaching role"),
        widget=deform.widget.SelectWidget(
            values = (
                ("", "- Select -"),
                ('Chief Examiner', 'Chief Examiner'),
                ('Lecturer', 'Lecturer'),
                ('Admin Tutor', 'Admin Tutor'),
                ('Tutor', 'Tutor'),
            )
        ),
    )

    teaching_unit = colander.SchemaNode(
        colander.String(),
        title=_("Teaching unit"),
    )

    joined_year = colander.SchemaNode(
        colander.String(),
        validator=colander.All(
            validators.Length(min=1),
            colander.Regex("^\d{4}$", msg=("Must have only number")),
        ),
        title=_("Year joined Monash"),
    )

    years_of_experience = colander.SchemaNode(
        colander.String(),
        validator=colander.All(
            validators.Length(min=1),
            colander.Regex("^\d+$", msg=("Must have only number")),
        ),
        title=_("Year of teaching experience"),
    )
