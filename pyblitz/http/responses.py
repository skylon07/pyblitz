import requests

def _noTransform(responseJson):
    return responseJson

class Response:
    def __init__(self, response: requests.Response):
        pass # TODO

    def transform(self, SchemaClass, transformFn=_noTransform):
        pass # TODO
