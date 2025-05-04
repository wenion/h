def hasCommandKey(main_string):
    return any(sub in main_string for sub in [
        "`Meta`",
        "`Shift`",
        "`Alt`",
        "`Ctrl`",
        "`ArrowLeft`",
        "`ArrowRight`",
    ])

def binary_pairs(eg: str, value: bool) -> str:
    eg = eg.lower()
    if eg == 'yes' or eg == 'no':
        return 'Yes' if value else 'No'
    if eg == 'on' or eg == 'off':
        return 'On' if value else 'Off'
    if eg == 'enabled' or eg == 'disabled':
        return 'Enabled' if value else 'Disabled'
    if eg == 'enable' or eg == 'disable':
        return 'Enable' if value else 'Disable'
    if eg == 'pass' or eg == 'fail':
        return 'Pass' if value else 'Fail'
    if eg == 'include' or eg == 'exclude':
        return 'Include' if value else 'Exclude'

def _user_event_finite_state(event, state):
    if state["state"] == "init":
        # Ignore
        if event["title"] == "push":
            return {**event, "state": "ignore"}, event
        elif event["type"] == "pointerdown" and event["title"] == "click" and event["tag_name"] == "HYPOTHESIS-SIDEBAR":
            return {**event, "state": "ignore"}, event
        elif event["type"] == "client" and event["title"] == "click" and event["tag_name"] == "EXPERT-TRACE_CLOSE":
            return {**event, "state": "ignore"}, event
        elif event["tag_name"] == "HYPOTHESIS-ADDER":
            return {**event, "state": "ignore"}, event
        elif event["title"] == "click" and event["type"] == "client":
            return {**event, "state": "ignore"}, event
        elif event["type"] == "contextmenu":
            return {**event, "state": "ignore"}, event
        elif event["type"] == "mouseup" and event["title"] == "select":
            return {**event, "state": "ignore"}, event
        # Nav
        elif event["tag_name"] == "Navigate":
            return {**event, "state": "n1"}, event
        elif event["tag_name"] == "Switch":
            return {**event, "state": "n1"}, event
        elif event["tag_name"] == "RECORD" and event["description"] == "start":
            return {**event, "state": "ignore"}, event
        elif event["tag_name"] == "RECORD" and event["description"] == "finish":
            return {**event, "state": "ignore"}, event
        # Change
        elif event["type"] == "change" and event["title"] == "type" and event["tag_name"] == "CHECKBOX":
            if state.get("type") == "pointerdown":
                return {**event, "title": "click", "state": "cb1", "payload": state["description"]}, event
            return {**event, "title": "click", "state": "cb1"}, event
        elif event["type"] == "change" and event["title"] == "type" and event["tag_name"] == "SELECT":
            return {**event, "title": "select", "state": "cs1", "description": None}, event
        elif event["type"] == "change" and event["title"] == "type" and event["tag_name"] != "SELECT" and event["tag_name"] != "CHECKBOX":
            return {**event, "state": "t1"}, event
        # Type
        elif event["type"] == "keydown" and event["title"] == "type" and hasCommandKey(event["description"]):
            return {**event, "state": "ignore"}, event
        elif event["type"] == "keydown" and event["title"] == "type" and not hasCommandKey(event["description"]) and event["description"].strip() == "":
            return {**event, "state": "ignore"}, event
        elif event["type"] == "keydown" and event["title"] == "type" and not hasCommandKey(event["description"]) and event["description"].strip() != "":
            return {**event, "state": "t1"}, event
        elif event["type"] == "keydown" and event["title"] == "copy":
            return {**event, "state": "cp1"}, event
        elif event["type"] == "copy" and event["title"] == "copy":
            return {**event, "state": "cp2"}, event
        elif event["type"] == "keydown" and event["title"] == "paste":
            return {**event, "state": "ps1"}, event
        elif event["type"] == "paste" and event["title"] == "paste":
            return {**event, "state": "ps2"}, event
        # Select/Click text
        elif event.get("type") == "pointerdown" and event.get("title") == "click":
            tag = event.get("tag_name")
            if tag == "SELECT":
                return {**event, "state": "cs1"}, event
            elif tag == "CHECKBOX":
                return {**event, "state": "c7"}, event
            elif tag == "BUTTON":
                return {**event, "state": "c2"}, event
            else:
                return {**event, "state": "c1"}, event
        else:
            return {**event, "state": "i"}, event
    elif state["state"] == "i":
        return {**state, "state": "end"}, event
    elif state["state"] == "n1":
        if event["tag_name"] == "Navigate" and event["url"] == state["url"]:
            return {**event, "state": "n1"}, event
        elif event["tag_name"] == "Navigate" and event["url"] != state["url"]:
            return {**event, "state": "n2"}, event
        elif event["tag_name"] == "Switch" and event["url"] == state["url"]:
            return {**event, "state": "n1"}, event
        elif event["tag_name"] == "Switch" and event["url"] != state["url"]:
            return {**event, "state": "n2"}, event
        elif event["tag_name"] == "RECORD" and event["description"] == "start":
            return {**state, "state": "n1"}, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "n2":
        if event["tag_name"] == "Navigate" and event["url"] == state["url"]:
            return {**event, "state": "n2"}, event
        elif event["tag_name"] == "Navigate" and event["url"] != state["url"]:
            return {**event, "state": "n1"}, event
        elif event["tag_name"] == "Switch" and event["url"] == state["url"]:
            return {**event, "state": "n2"}, event
        elif event["tag_name"] == "Switch" and event["url"] != state["url"]:
            return {**event, "state": "n1"}, event
        elif event["tag_name"] == "RECORD" and event["description"] == "start":
            return {**state, "state": "n2"}, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "c1":
        if event["type"] == "mouseup" and event["title"] == "select":
            return {**event, "state": "end"}, event
        elif event["type"] == "pointerdown" and event["title"] == "click" and event["tag_name"] != "SELECT" and event["description"] == state["description"]:
            return {**event, "state": "c1"}, event
        elif event["type"] == "contextmenu":
            return {**state, "state": "rc1"}, event
        elif event["type"] == "submit":
            return {**event, "client_x": state["client_x"], "client_y": state["client_y"], "state": "end"}, event
        # elif event["type"] == "change" and event["title"] == "type" and event["tag_name"] == "CHECKBOX":
        #     return {**event, "state": "cb1", "image": state["image"],"payload": state["description"]}, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "c2":
        return {**state, "state": "end"}, event
    elif state["state"] == "c7":
        if event["type"] == "change" and event["title"] == "type" and event["tag_name"] == "CHECKBOX" and event["description"] == state["description"]:
            return {**state, "title": "click", "state": "cb1"}, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "cb1":
        value = None
        name = None
        interaction_context = state.get('interaction_context', None)
        if interaction_context:
            if 'name' in interaction_context:
                name = str(interaction_context['name'])
            if 'value' in interaction_context:
                payload = state.get('payload', None)
                if payload and isinstance(interaction_context['value'], bool):
                    value = binary_pairs(payload, interaction_context['value'])
                else:
                    value = str(interaction_context['value'])

        if name and value:
            description = "Select \"" + value + "\" for the \"" + name + "\" option."
            return {**state, "title": "select", "description": description, "state": "end"}, event
        elif value and not name:
            description = "Select \"" + value + "\""
            return {**state, "title": "select", "description": description, "state": "end"}, event
        else:
            description = "Select the \"" + state['description'] + "\" option."
            return {**state, "title": "select", "state": "end"}, event
    elif state["state"] == "cs1":
        if event["type"] == "change" and event["title"] == "type" and event["tag_name"] == "SELECT":
            description = event["description"].strip()
            dropdown = " from the \"" + state["description"].strip() + "\"." if state["description"] else "."
            return {
                **event,
                "state": "cs2",
                "title": "select",
                "description": "Select \"" + description + "\"" + dropdown
                }, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "cs2":
        return {**state, "state": "end"}, event
    elif state["state"] == "t1":
        if event["type"] == "keydown" and event["title"] == "type" and event["description"] == state["description"] and event["tag_name"] != "SELECT" and event["tag_name"] != "CHECKBOX":
            return {**state, "state": "t1"}, event
        elif event["type"] == "change" and event["title"] == "type" and event["tag_name"] != "SELECT" and event["tag_name"] != "CHECKBOX":
            return {**event, "state": "t1"}, event
        elif event["type"] == "scroll":
            return {**state, "state": "t1"}, event
        else:
            description = state["description"] if state["description"] != "" else "Clear content"
            return {**state, "description": description, "state": "end"}, event
    elif state["state"] == "cp1":
        if event["type"] == "copy" and event["title"] == "copy":
            return {**event, "state": "cp2"}, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "cp2":
        if event["type"] == "keydown" and event["title"] == "copy" and event["description"] == state["description"]:
            return {**event, "state": "cp2"}, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "ps1":
        if event["type"] == "paste" and event["title"] == "paste":
            return {**event, "state": "ps2"}, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "ps2":
        if event["type"] == "keydown" and event["title"] == "paste" and event["description"] == state["description"]:
            return {**event, "state": "ps2"}, event
        elif event["type"] == "change" and event["description"] == state["description"]:
            return {**event, "state": "ps2"}, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "rc1":
        if event["type"] == "copy" and event["title"] == "copy":
            return {**event, "state": "cp2"}, event
        elif event["type"] == "paste" and event["title"] == "paste":
            return {**event, "state": "ps2"}, event
        else:
            return {**event, "state": "ignore"}, event
    else:
        return state, event


def address_events(events):
    if not len(events):
        return events

    s = {**events[0], "state": "init"}

    better = []

    index = 0

    while index < len(events):
        i = events[index]

        [state, event] = _user_event_finite_state(i, s)
        if state["state"] == "end":
            better.append(state)
            s = {**state, "state": "init"}
        elif state["state"] == "ignore":
            s = {**state, "state": "init"}
            index += 1
        else:
            s = state
            index += 1

    # remove repeat
    seen_ids = set()
    unique_data = []

    for item in better:
        if item['pk'] not in seen_ids:
            item.pop('interaction_context')
            item.pop('payload', None)
            unique_data.append(item)
            seen_ids.add(item['pk'])

    return unique_data
