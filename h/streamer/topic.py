import logging
from collections import namedtuple

from h.pubsub import Sub
from h.streamer import websocket
from h.streamer.contexts import request_context
from h.streamer.topic_meta import Topic, TASK_EXCHANGE, TASK_TOPIC, TRACE_EXCHANGE, TRACE_TOPIC
from h.tasks import user_events

__all__ = (
    "Topic",
    "TASK_EXCHANGE",
    "TASK_TOPIC",
    "TRACE_EXCHANGE",
    "TRACE_TOPIC",
)

log = logging.getLogger(__name__)

# TODO Multithreading issues
def trace_process_messages(settings, routing_key, raise_error=True):
    """
    Configure, start, and monitor a realtime consumer for the specified routing
    key.

    This sets up a :py:class:`h.realtime.Consumer` to route messages from
    `routing_key` to the passed `work_queue`, and starts it. The consumer
    should never return. If it does, this function will raise an exception.
    """

    # call twice todo
    def callback(payload, message):
        try:
            # user_events.add_event.delay(payload)
            print('receive >>>', payload['type'])
        except Full:  # pragma: no cover
            log.warning(
                "Streamer work queue full! Unable to queue message from "
                "h.realtime having waited 0.1s: giving up."
            )

    consumer = Sub(
        settings,
        TRACE_EXCHANGE,
        routing_key=routing_key,
        identifier="streamer",
        callback=callback,
        )
    consumer.run()

    if raise_error:
        raise RuntimeError("Realtime consumer quit unexpectedly!")


def task_process_messages(settings, routing_key, work_queue, raise_error=True):
    """
    Configure, start, and monitor a realtime consumer for the specified routing key.

    This sets up a :py:class:`h.realtime.Consumer` to route messages from
    `routing_key` to the passed `work_queue`, and starts it. The consumer
    should never return. If it does, this function will raise an exception.
    """

    def callback(payload, message):
        message = Topic(topic=routing_key, payload=payload)
        try:
            work_queue.put(message, timeout=0.1)
        except Full:  # pragma: no cover
            log.warning(
                "Streamer work queue full! Unable to queue message from "
                "h.realtime having waited 0.1s: giving up."
            )

    consumer = Sub(
        settings,
        TASK_EXCHANGE,
        routing_key=routing_key,
        identifier="streamer",
        callback=callback,
        )
    consumer.run()

    if raise_error:
        raise RuntimeError("Realtime consumer quit unexpectedly!")


def handle_message(message, registry, session):
    # N.B. We iterate over a non-weak list of instances because there's nothing
    # to stop connections being added or dropped during iteration, and if that
    # happens Python will throw a "Set changed size during iteration" error.
    sockets = list(websocket.WebSocket.instances)
    for socket in sockets:
        if not hasattr(socket, "client_id") or \
            message.payload["client_id"] != socket.client_id:
            continue
        # TODO
        with request_context(registry) as request:
            print("message from tad", message.payload, socket.client_id)

            # socket.send_json(reply)
