def _user_event_finite_state(event, state):
    if state["state"] == "init":
        if event["tagName"] == "Navigate":
            return {**event, "state": "n1"}, event
        if event["title"] == "switch to":
            return {**event, "state": "n1"}, event
        elif event["tagName"] == "RECORD" and event["description"] == "start":
            return {**event, "state": "ignore"}, event
        elif event["tagName"] == "RECORD" and event["description"] == "finish":
            return {**event, "state": "ignore"}, event
        elif event["tagName"] == "EXPERT-TRACE_CLOSE":
            return {**event, "state": "ignore"}, event
        elif event["type"] == "pointerdown" and event["tagName"] == "HYPOTHESIS-SIDEBAR":
            return {**event, "state": "ignore"}, event
        elif event["type"] == "pointerdown" and event["tagName"] != "HYPOTHESIS-SIDEBAR":
            return {**event, "state": "c1"}, event
        elif event["type"] == "mouseup" and event["title"] == "select":
            return {**event, "state": "s1"}, event
        elif event["title"] == "copy":
            return {**event, "state": "cp1"}, event
        elif event["title"] == "paste":
            return {**event, "state": "p1"}, event
        elif event["title"] == "type" and event["description"] == "":
            return {**event, "state": "ignore"}, event
        elif event["title"] == "type" and event["description"] != "":
            return {**event, "state": "t1"}, event
        elif event["type"] == "client" and event["title"] == "click" and event["tagName"] == "EXPERT-TRACE_CLOSE":
            return {**event, "state": "ignore"}, event
        else:
            return {**event, "state": "end"}, event
    elif state["state"] == "n1":
        if event["tagName"] == "Navigate" and event["url"] == state["url"]:
            return {**event, "state": "n1"}, event
        elif event["tagName"] == "Navigate" and event["url"] != state["url"]:
            return {**event, "state": "n2"}, event
        elif event["title"] == "switch to" and event["url"] == state["url"]:
            return {**event, "state": "n1"}, event
        elif event["title"] == "switch to" and event["url"] != state["url"]:
            return {**event, "state": "n2"}, event
        elif event["tagName"] == "RECORD" and event["description"] == "start":
            return state, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "n2":
        if event["tagName"] == "Navigate" and event["url"] == state["url"]:
            return {**event, "state": "n2"}, event
        elif event["tagName"] == "Navigate" and event["url"] != state["url"]:
            return {**event, "state": "n1"}, event
        elif event["title"] == "switch to" and event["url"] == state["url"]:
            return {**event, "state": "n2"}, event
        elif event["title"] == "switch to" and event["url"] != state["url"]:
            return {**event, "state": "n1"}, event
        elif event["tagName"] == "RECORD" and event["description"] == "start":
            return state, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "c1":
        if event["title"] == "click" and event["type"] == "pointerdown" and event["clientX"] == state["clientX"] and event["clientY"] == state["clientY"] and event["tagName"] == state["tagName"]:
            return {**event, "state": "c1"}, event
        elif event["type"] == "mouseup" and event["title"] == "select":
            return {**event, "state": "s1"}, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "s1":
        if event["type"] == "mouseup" and event["title"] == "select":
            return {**event, "state": "s1"}, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "t1":
        if event["title"] == "type" and event["description"] == state["description"]:
            return {**event, "state": "t1"}, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "cp1":
        if event["title"] == "copy" and event["description"] == state["description"]:
            return {**event, "state": "cp1"}, event
        else:
            return {**state, "state": "end"}, event
    elif state["state"] == "p1":
        if event["title"] == "paste":
            return {**event, "state": "p1"}, event
        else:
            return {**state, "state": "end"}, event
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
