import logging
from collections import namedtuple

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
