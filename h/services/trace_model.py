def hasCommandKey(main_string):
    return any(sub in main_string for sub in [
        "`Meta`",
        "`Shift`",
        "`Alt`",
        "`Ctrl`",
        "`ArrowLeft`",
        "`ArrowRight`",
    ])

def _user_event_finite_state(event, state):
    if state["state"] == "init":
        # Ignore
        if event["title"] == "push":
            return {**event, "state": "ignore"}, event
        elif event["type"] == "pointerdown" and event["title"] == "click" and event["tagName"] == "HYPOTHESIS-SIDEBAR":
            return {**event, "state": "ignore"}, event
        elif event["type"] == "client" and event["title"] == "click" and event["tagName"] == "EXPERT-TRACE_CLOSE":
            return {**event, "state": "ignore"}, event
        elif event["tagName"] == "HYPOTHESIS-ADDER":
            return {**event, "state": "ignore"}, event
        elif event["title"] == "click" and event["type"] == "client":
            return {**event, "state": "ignore"}, event
        # Nav
        elif event["tagName"] == "Navigate":
            return {**event, "state": "n1"}, event
        elif event["tagName"] == "Switch":
            return {**event, "state": "n1"}, event
        elif event["tagName"] == "RECORD" and event["description"] == "start":
            return {**event, "state": "ignore"}, event
        elif event["tagName"] == "RECORD" and event["description"] == "finish":
            return {**event, "state": "ignore"}, event
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
        # Select text
        elif event["type"] == "pointerdown" and event["title"] == "click" and event["tagName"] != "SELECT":
            return {**event, "state": "c1"}, event
        elif event["type"] == "pointerdown" and event["title"] == "click" and event["tagName"] == "SELECT":
            return {**event, "state": "cs1"}, event
        else:
            return {**event, "state": "end"}, event
    elif state["state"] == "n1":
        if event["tagName"] == "Navigate" and event["url"] == state["url"]:
            return {**event, "state": "n1"}, event
        elif event["tagName"] == "Navigate" and event["url"] != state["url"]:
            return {**event, "state": "n2"}, event
        elif event["tagName"] == "Switch" and event["url"] == state["url"]:
            return {**event, "state": "n1"}, event
        elif event["tagName"] == "Switch" and event["url"] != state["url"]:
            return {**event, "state": "n2"}, event
        elif event["tagName"] == "RECORD" and event["description"] == "start":
            return {**state, "state": "n1"}, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "n2":
        if event["tagName"] == "Navigate" and event["url"] == state["url"]:
            return {**event, "state": "n2"}, event
        elif event["tagName"] == "Navigate" and event["url"] != state["url"]:
            return {**event, "state": "n1"}, event
        elif event["tagName"] == "Switch" and event["url"] == state["url"]:
            return {**event, "state": "n2"}, event
        elif event["tagName"] == "Switch" and event["url"] != state["url"]:
            return {**event, "state": "n1"}, event
        elif event["tagName"] == "RECORD" and event["description"] == "start":
            return {**state, "state": "n2"}, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "c1":
        if event["type"] == "mouseup" and event["title"] == "select":
            return {**event, "state": "end"}, event
        elif event["type"] == "pointerdown" and event["title"] == "click" and event["tagName"] != "SELECT" and event["description"] == state["description"]:
            return {**event, "state": "c1"}, event
        elif event["type"] == "contextmenu":
            return {**state, "state": "rc1"}, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "cs1":
        if event["type"] == "change" and event["title"] == "type" and event["tagName"] == "SELECT":
            return {**event, "state": "end"}, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "t1":
        if event["type"] == "keydown" and event["title"] == "type" and event["description"] == state["description"] and event["tagName"] != "SELECT":
            return {**state, "state": "t1"}, event
        else:
            return {**state, "state": "end"}, event
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

    start_state = {**events[0], "state": "init"}

    better = []
    s = start_state

    for i in events:
        [state, event] = _user_event_finite_state(i, s)
        if state["state"] == "end":
            better.append(state)
            s = {**state, "state": "init"}
            [state, event] = _user_event_finite_state(i, s)
        elif state["state"] == "ignore":
            s = {**state, "state": "init"}
            [state, event] = _user_event_finite_state(i, s)

        s = state
        if state["state"] == "end":
            better.append(state)

    # remove repeat
    seen_ids = set()
    unique_data = []

    for item in better:
        if item['id'] not in seen_ids:
            unique_data.append(item)
            seen_ids.add(item['id'])

    return unique_data
