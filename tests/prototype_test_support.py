"""AppTest bridge for a Streamlit 1.67 Components v2 browser event."""

import json

from streamlit.components.v2.bidi_component.main import _make_trigger_id


def component_proto(app):
    return app.get("bidi_component")[0].proto


def prototype_data(app):
    return json.loads(component_proto(app).json)


def dispatch(app, kind, *, revision=None, **fields):
    # AppTest can inspect the proto but has no browser or v2 trigger helper.
    proto = component_proto(app)
    widgets = app._tree.get_widget_states()
    event = {"kind": kind, "revision": revision or prototype_data(app)["revision"], **fields}
    widgets.widgets.add(
        id=_make_trigger_id(proto.id, "events"),
        json_trigger_value=json.dumps([{"event": "action", "value": event}]),
    )
    return app._run(widgets)
