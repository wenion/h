from h.celery import celery, get_task_logger

log = get_task_logger(__name__)


@celery.task
def generate_shareflows(session_id):
    """Task to add the new Shareflow metadata table."""

    service = celery.request.find_service(name="shareflow")
    shareflow_metadata = service.get_shareflow_metadata_by_session_id(session_id)

    service.generate_shareflows(shareflow_metadata, 1)

@celery.task
def regenerate_shareflows(session_id):
    """Task to add the new Shareflow metadata table."""

    service = celery.request.find_service(name="shareflow")
    shareflow_metadata = service.get_shareflow_metadata_by_session_id(session_id)

    service.regenerate_shareflows(shareflow_metadata)
