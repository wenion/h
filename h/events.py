class AnnotationEvent:
    """An event representing an action on an annotation."""

    def __init__(self, request, annotation_id, action):
        self.request = request
        self.annotation_id = annotation_id
        self.action = action


class ShareflowMetadataEvent:
    """An event representing an action on an shareflow metadata."""

    def __init__(self, request, shareflow_metadata_pk, shareflow_metadata_id):
        self.request = request
        self.index = shareflow_metadata_pk
        self.shareflow_metadata_id = shareflow_metadata_id
