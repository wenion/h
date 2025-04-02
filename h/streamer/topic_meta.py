import logging
from collections import namedtuple

from h.pubsub import Pub

log = logging.getLogger(__name__)


# Mapping incoming message type to handler function. Handlers are added inline
# below.
TRACE_EXCHANGE = "trace"
TASK_EXCHANGE = "process.task"
TRACE_TOPIC = "request.user.event"
TASK_TOPIC = "response.user.event"

PULL_EXCHANGE = "pull"
PUSH_EXCHANGE = "push"
PULL_TOPIC = "pull.user.tab"
PUSH_TOPIC = "push.user.tab"

Topic = namedtuple("Topic", ["routing_key", "payload"])


class TraceTopicPub(Pub):
    def __init__(self, settings):
        super().__init__(settings, TRACE_EXCHANGE)

    def send_trace(self, payload):
        self.publish(payload, TRACE_TOPIC)

class PushTopicPub(Pub):
    def __init__(self, settings):
        super().__init__(settings, PUSH_EXCHANGE)
    
    def send_push(self, payload):
        self.publish(payload, PUSH_TOPIC)
