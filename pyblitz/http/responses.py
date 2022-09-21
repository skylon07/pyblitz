import requests
import json

from ..common import Schema


class Response:
    def __init__(self, response: requests.Response):
        self._response = response
        self._jsonDict = json.loads(response.text)

    @property
    def status(self):
        return self._response.status_code

    def transform(self, transformFn):
        transformResult = transformFn(self._jsonDict)
        (SchemaClass, transDict) = self._checkTransformation(transformResult)
        return SchemaClass.fromSerialized(transDict)

    def transformGen(self, transformGenFn):
        return tuple(
            SchemaClass.fromSerialized(transDict)
            for transformResult in transformGenFn(self._jsonDict)
            for (SchemaClass, transDict) in [self._checkTransformation(transformResult)]
        )
    
    def _checkTransformation(self, transformReturn):
        if not type(transformReturn) is tuple or len(transformReturn) != 2:
            raise TypeError("Transform functions must return a tuple of size-2")

        (SchemaClass, transDict) = transformReturn
        if not issubclass(SchemaClass, Schema):
            raise TypeError("First value in returned transform-tuple must be one of the Schema classes generated in the api file")
        
        return transformReturn

