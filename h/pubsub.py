import base64
import random
import struct

import kombu
from kombu.exceptions import LimitExceeded, OperationalError
from kombu.mixins import ConsumerMixin
from kombu.pools import producers as producer_pool

from h.exceptions import RealtimeMessageQueueError
from h.tasks import RETRY_POLICY_QUICK, RETRY_POLICY_VERY_QUICK
from h.realtime import get_connection


class Sub(ConsumerMixin):
    """
    A realtime consumer.

    Listens to the configured routing key and calls
    the wrapped handler function on receiving a matching message.

    Conforms to the :py:class:`kombu.mixins.ConsumerMixin` interface.

    :param settings: A dictionary containing the message broker's
        connection details.
        Expected format : {'broker_url': '<address>'}
        Example: {'broker_url': 'amqp://guest:guest@localhost:5672//'}
    :param name: Exchange'name. Predefine.
    :param routing_key: listen to messages with this routing key. Predefine.
    :param identifier: The listener's name to identified.
    :param callback: the function which gets called when a messages arrives
    """

    def __init__(
        self, settings, exchange_name, routing_key, identifier, callback
    ):
        self.connection = get_connection(settings, fail_fast=True)
        self.exchange_name = exchange_name
        self.routing_key = routing_key
        self.identifier = identifier
        self.handler = callback
        self.exchange = kombu.Exchange(
            exchange_name, type="topic", durable=True, delivery_mode="persistent"
        )

    def get_consumers(
        self, Consumer, channel
    ):  # pylint: disable=arguments-renamed
        name = self.generate_queue_name()
        queue = kombu.Queue(
            name,
            self.exchange,
            durable=False,
            routing_key=self.routing_key,
            auto_delete=True,
        )
        return [Consumer(queues=[queue], callbacks=[self.process_message])]

    def generate_queue_name(self):
        return f"{self.exchange_name}-{self.identifier}-{self._random_id()}"

    def process_message(self, body, message):
        """
        Handle a realtime message by acknowledging it and then calling the
        wrapped handler.
        """

        self.handler(body)
        message.ack()

    @staticmethod
    def _random_id():
        """Generate a short random string."""
        data = struct.pack("Q", random.getrandbits(64))
        return base64.urlsafe_b64encode(data).strip(b"=")


def publish(connection, exchange, routing_key, payload):
    """
        This functino is used in the streamer service only.
    """
    try:
        with producer_pool[connection].acquire(
            block=True, timeout=1
        ) as producer:
            producer.publish(
                payload,
                exchange=exchange,
                declare=[exchange],
                routing_key=routing_key,
                retry=True,
                # This is the retry for the producer, the connection
                # retry is separate
                retry_policy=RETRY_POLICY_VERY_QUICK,
            )

    except (OperationalError, LimitExceeded) as err:
        # If we fail to connect (OperationalError), or we don't get a
        # producer from the pool in time (LimitExceeded) raise
        raise RealtimeMessageQueueError() from err
