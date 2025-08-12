class RPCService:
    def __init__(self, request):
        self.request = request

    def query(self, query: str):
        return self.request.rpc.call("query", {'q': query})

    def summary(self, title, url, content):
        data = {
            'title': title,
            'url': url,
            'content': content
        }
        return self.request.rpc.call("summary", data)

    def segmentation(self, content):
        return self.request.rpc.call(
            "segmentation",
            {'content': content}
        )

    def ingest_knowledge(self, title: str, content: str, url: str, repository: str):
        return self.request.rpc.call(
            "ingest_knowledge",
            {
                'title': title,
                'content': content,
                'url': url,
                'repository': repository
            }
        )

def rpc_service_factory(_context, request):
    return RPCService(request)
