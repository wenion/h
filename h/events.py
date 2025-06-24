class AnnotationEvent:
    """An event representing an action on an annotation."""

    def __init__(self, request, annotation_id, action):
        self.request = request
        self.annotation_id = annotation_id
        self.action = action


class ShareflowMetadataEvent:
    """An event representing an action on an shareflow metadata."""

    def __init__(self, request, shareflow_metadata):
        self.request = request
        self.data = shareflow_metadata

class ShareflowDataListEvent:
    """An event representing an action on an shareflow data list."""

    def __init__(self, request, data):
        self.request = request
        self.data = data
