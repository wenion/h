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
                ('Public Health and Preventive Medicine', 'Public Health and Preventive Medicine'),
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

    campus = colander.SchemaNode(
        colander.String(),
        title=_("Campus"),
        widget=deform.widget.SelectWidget(
            values = (
                ("", "- Select -"),
                ('Clayton', 'Clayton campus'),
                ('Caulfield', 'Caulfield campus'),
                ('Peninsula', 'Peninsula campus'),
                ('Parkville', 'Parkville campus'),
                ('Law Chambers', 'Law Chambers'),
                ('750 Collins Street', '750 Collins Street'),
                ('553 St. Kilda Rd', '553 St. Kilda Rd'),
                ('Malaysia campus', 'Malaysia campus'),
                ('Indonesia campus', 'Indonesia campus'),
                ('Monash Suzhou, China', 'Monash Suzhou, China'),
                ('IITB Monash Academy, India', 'IITB Monash Academy, India'),
                ('Prato Centre, Italy', 'Prato Centre, Italy'),
            )
        ),
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
