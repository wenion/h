import json

from deform.compat import string_types, text_
from deform.widget import Widget
from colander import Mapping, String, Invalid, SchemaNode
from iso8601.iso8601 import ISO8601_REGEX


_BLANK = text_("")


class _null:
    """Represents a null value in colander-related operations."""

    def __nonzero__(self):
        return False

    # py3 compat
    __bool__ = __nonzero__

    def __repr__(self):
        return '<colander.null>'

    def __reduce__(self):
        return 'null'  # when unpickled, refers to "null" below (singleton)


null = _null()



class _PossiblyEmptyString(String):
    def deserialize(self, node, cstruct):
        if cstruct == "":
            return _BLANK  # String.deserialize returns null
        return super(_PossiblyEmptyString, self).deserialize(node, cstruct)


class _StrippedString(_PossiblyEmptyString):
    def deserialize(self, node, cstruct):
        appstruct = super(_StrippedString, self).deserialize(node, cstruct)
        if isinstance(appstruct, string_types):
            appstruct = appstruct.strip()
        return appstruct


class DateInputWidget(Widget):
    """
    Renders a date picker widget.

    The default rendering is as a native HTML5 date input widget,
    falling back to pickadate (https://github.com/amsul/pickadate.js.)

    Most useful when the schema node is a ``colander.Date`` object.

    **Attributes/Arguments**

    options
        Dictionary of options for configuring the widget (eg: date format)

    template
        The template name used to render the widget.  Default:
        ``dateinput``.

    readonly_template
        The template name used to render the widget in read-only mode.
        Default: ``readonly/textinput``.
    """

    template = "dateinput"
    readonly_template = "readonly/textinput"
    type_name = "date"
    requirements = (("modernizr", None), ("pickadate", None))
    default_options = (
        ("format", "yyyy-mm-dd"),
        ("selectMonths", True),
        ("selectYears", True),
    )
    options = None

    _pstruct_schema = Mapping()
    # SchemaNode(
    #     Mapping(),
    #     SchemaNode(_StrippedString(), name="date"),
    #     SchemaNode(_StrippedString(), name="date_submit", missing=""),
    # )

    def serialize(self, field, cstruct, **kw):
        if cstruct in (null, None):
            cstruct = ""
        readonly = kw.get("readonly", self.readonly)
        template = readonly and self.readonly_template or self.template
        options = dict(
            kw.get("options") or self.options or self.default_options
        )
        options["formatSubmit"] = "yyyy-mm-dd"
        kw.setdefault("options_json", json.dumps(options))
        values = self.get_template_values(field, cstruct, kw)
        return field.renderer(template, **values)

    def deserialize(self, field, pstruct):
        if pstruct in ("", null):
            return null
        return pstruct
        # try:
        #     validated = self._pstruct_schema.deserialize(pstruct)
        # except Invalid as exc:
        #     raise Invalid(field.schema, "Invalid pstruct: %s" % exc)
        # return validated["date_submit"] or validated["date"]


class TimeInputWidget(Widget):
    """
    Renders a time picker widget.

    The default rendering is as a native HTML5 time input widget,
    falling back to pickadate (https://github.com/amsul/pickadate.js.)

    Most useful when the schema node is a ``colander.Time`` object.

    **Attributes/Arguments**

    style
        A string that will be placed literally in a ``style`` attribute on
        the text input tag.  For example, 'width:150px;'.  Default: ``None``,
        meaning no style attribute will be added to the input tag.

    options
        Options for configuring the widget (eg: date format)

    template
        The template name used to render the widget.  Default:
        ``timeinput``.

    readonly_template
        The template name used to render the widget in read-only mode.
        Default: ``readonly/timeinput``.
    """

    template = "timeinput"
    readonly_template = "readonly/textinput"
    type_name = "time"
    size = None
    style = None
    requirements = (("modernizr", None), ("pickadate", None))
    default_options = (("format", "HH:i"),)

    _pstruct_schema = SchemaNode( #Mapping()
        Mapping(),
        # SchemaNode(_StrippedString(), name="time"),
        # SchemaNode(_StrippedString(), name="time_submit", missing=""),
    )

    def __init__(self, *args, **kwargs):
        self.options = dict(self.default_options)
        self.options["formatSubmit"] = "HH:i"
        Widget.__init__(self, *args, **kwargs)

    def serialize(self, field, cstruct, **kw):
        if cstruct in (null, None):
            cstruct = ""
        readonly = kw.get("readonly", self.readonly)
        template = readonly and self.readonly_template or self.template
        options = dict(
            kw.get("options") or self.options or self.default_options
        )
        options["formatSubmit"] = "HH:i"
        kw.setdefault("options_json", json.dumps(options))
        values = self.get_template_values(field, cstruct, kw)
        return field.renderer(template, **values)

    def deserialize(self, field, pstruct):
        if pstruct in ("", null):
            return null
        return pstruct
        # try:
        #     validated = self._pstruct_schema.deserialize(pstruct)
        # except Invalid as exc:
        #     raise Invalid(field.schema, text_("Invalid pstruct: %s" % exc))
        # return validated["time_submit"] or validated["time"]


class DateTimeInputWidget(Widget):
    """
    Renders a datetime picker widget.

    The default rendering is as a pair of inputs (a date and a time) using
    pickadate.js (https://github.com/amsul/pickadate.js).

    Used for ``colander.DateTime`` schema nodes.

    **Attributes/Arguments**

    date_options
        A dictionary of date options passed to pickadate.

    time_options
        A dictionary of time options passed to pickadate.

    template
        The template name used to render the widget.  Default:
        ``dateinput``.

    readonly_template
        The template name used to render the widget in read-only mode.
        Default: ``readonly/textinput``.
    """

    template = "datetimeinput"
    readonly_template = "readonly/datetimeinput"
    type_name = "datetime"
    requirements = (("modernizr", None), ("pickadate", None))
    default_date_options = (
        ("format", "yyyy-mm-dd"),
        ("selectMonths", True),
        ("selectYears", True),
    )
    date_options = None
    default_time_options = (("format", "h:i A"), ("interval", 30))
    time_options = None

    _pstruct_schema = Mapping() # SchemaNode(
        # Mapping(),
        # SchemaNode(_StrippedString(), name="date"),
        # SchemaNode(_StrippedString(), name="time"),
        # SchemaNode(_StrippedString(), name="date_submit", missing=""),
        # SchemaNode(_StrippedString(), name="time_submit", missing=""),
    # )

    def serialize(self, field, cstruct, **kw):
        if cstruct in (null, None):
            cstruct = ""
        readonly = kw.get("readonly", self.readonly)
        if cstruct:
            parsed = ISO8601_REGEX.match(cstruct)
            if parsed:  # strip timezone if it's there
                timezone = parsed.groupdict()["timezone"]
                if timezone and cstruct.endswith(timezone):
                    cstruct = cstruct[: -len(timezone)]

        try:
            date, time = cstruct.split("T", 1)
            try:
                # get rid of milliseconds
                time, _ = time.split(".", 1)
            except ValueError:
                pass
            kw["date"], kw["time"] = date, time
        except ValueError:  # need more than one item to unpack
            kw["date"] = kw["time"] = ""

        date_options = dict(
            kw.get("date_options")
            or self.date_options
            or self.default_date_options
        )
        date_options["formatSubmit"] = "yyyy-mm-dd"
        kw["date_options_json"] = json.dumps(date_options)

        time_options = dict(
            kw.get("time_options")
            or self.time_options
            or self.default_time_options
        )
        time_options["formatSubmit"] = "HH:i"
        kw["time_options_json"] = json.dumps(time_options)

        values = self.get_template_values(field, cstruct, kw)
        template = readonly and self.readonly_template or self.template
        return field.renderer(template, **values)

    def deserialize(self, field, pstruct):
        if pstruct is null:
            return null
        else:
            return pstruct
            try:
                validated = self._pstruct_schema.deserialize(pstruct)
            except Invalid as exc:
                raise Invalid(field.schema, "Invalid pstruct: %s" % exc)
            # seriously pickadate?  oh.  right.  i forgot.  you're javascript.
            date = validated["date_submit"] or validated["date"]
            time = validated["time_submit"] or validated["time"]

            if not time and not date:
                return null

            result = "T".join([date, time])

            if not date:
                raise Invalid(field.schema, _("Incomplete date"), result)

            if not time:
                raise Invalid(field.schema, _("Incomplete time"), result)

            return result
