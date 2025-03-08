from h.celery import celery, get_task_logger
from h.services.trace_model import address_events

log = get_task_logger(__name__)


@celery.task
def add_shareflow_metadata(json_shareflow_metadata):
    """Task to add the new Shareflow metadata table."""
    session_id = json_shareflow_metadata['id']

    shareflow_service = celery.request.find_service(name="shareflow")
    shareflow_metadata = shareflow_service.read_shareflow_metadata_by_session_id(session_id)

    trace_service = celery.request.find_service(name="trace")
    all = trace_service.get_traces_by_session_id(session_id)

    traces = address_events(all)
    for trace in traces:
        detail = trace_service.get_trace_by_id(trace["id"])
        # TODO check is vaild image data
        image = detail.image

        shareflow_service.create_shareflow(
            trace,
            shareflow_metadata,
            image,
            shareflow_metadata.user_id
        )
