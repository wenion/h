"""
Producer for Celery progress.
"""

import logging

from h.celery import celery
from kombu import Exchange
from kombu.pools import producers

TRACE_EXCHANGE = "trace"
TRACE_TOPIC = "request.user.event"

RETRY_POLICY_VERY_QUICK = {
    "max_retries": 2,
    "interval_start": 0.2,
    "interval_step": 0.2,
    "interval_max": 0.5,
}

log = logging.getLogger(__name__)

trace_exchange = Exchange(
    TRACE_EXCHANGE,
    type="topic",
    durable=True,
    delivery_mode="persistent"
)


def publish(message: dict, routing_key: str, exchange_name: str, exchange: Exchange):
    with celery.connection_or_acquire() as conn:
        with producers[conn].acquire(block=True) as producer:
            producer.publish(
                message,
                exchange=exchange_name,
                routing_key=routing_key,
                declare=[exchange],
                retry=True,
                retry_policy=RETRY_POLICY_VERY_QUICK,
                serializer="json",
            )


def publish_trace_event(message: dict):
    return publish(message, TRACE_TOPIC, TRACE_EXCHANGE, trace_exchange)
