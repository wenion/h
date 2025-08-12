# pylint: disable=no-member # Instance of 'Celery' has no 'request' member
"""
A module for knowledge database manipulation.
"""

from h.celery import celery, get_task_logger

__all__ = ("ingest_knowledge",)

log = get_task_logger(__name__)


@celery.task(bind=True, max_retries=3, acks_late=True)
def ingest_knowledge(self, title, content, url, repo):
    rpc_svc = celery.request.find_service(name="rpc")
    try:
        rpc_svc.ingest_knowledge(title, content, url, repo)
    except Exception as e:
        log.warning(
            "ingest_knowledge failed"
        )
