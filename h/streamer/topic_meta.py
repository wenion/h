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

Topic = namedtuple("Topic", ["topic", "payload"])


class TraceTopicPub(Pub):
    def __init__(self, settings):
        super().__init__(settings, TRACE_EXCHANGE)
    
    def send_trace(self, payload):
        self.publish(payload, "request.user.event")
    
    def send_page(self, payload):
        self.publish(payload, "request.user.page")
