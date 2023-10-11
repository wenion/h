from slack_bolt import App
from slack_bolt.adapter.pyramid.handler import SlackRequestHandler

app = App()

@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)
    print(body)


@app.message("knock knock")
def ask_who(message, say):
    say("_Who's there 2?_")


handler = SlackRequestHandler(app)

def includeme(config):  # pragma: no cover
    config.registry["slack.app"] = app
    config.add_route("slack_events", "/slack/events")
    config.add_view(handler.handle, route_name="slack_events", request_method="POST")
