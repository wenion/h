import socket
from kombu import Consumer, Producer, Queue, uuid
from kombu.exceptions import TimeoutError

from h.realtime import get_connection


class RemoteProcedureCall:
    def __init__(self, request):
        self.connection = get_connection(request.registry.settings, fail_fast=True)
        self.callback_queue = Queue(uuid(), exclusive=True, auto_delete=True)

    def on_response(self, message):
        if message.properties['correlation_id'] == self.correlation_id:
            self.response = message.payload['result']

    def call(self, func, args, timeout=20):
        self.response = None
        self.correlation_id = uuid()
        with Producer(self.connection) as producer:
            producer.publish(
                {
                    "func": func,
                    **args
                },
                # args,
                exchange='',
                routing_key='rpc_queue',
                declare=[self.callback_queue],
                reply_to=self.callback_queue.name,
                correlation_id=self.correlation_id,
            )
        with Consumer(self.connection,
                      on_message=self.on_response,
                      queues=[self.callback_queue], no_ack=True):
            try:
                while self.response is None:
                    self.connection.drain_events(timeout=timeout)
            except (socket.timeout, TimeoutError):
                raise RuntimeError(f"RPC call timed out after {timeout} seconds")
            except Exception as e:
                raise RuntimeError(f"Unexpected error during RPC call: {e}")
        return self.response


def includeme(config):  # pragma: nocover
    config.add_request_method(RemoteProcedureCall, name="rpc", reify=True)
