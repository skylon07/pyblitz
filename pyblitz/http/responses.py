import requests
import json

from ..common import Schema


class Response:
    def __init__(self, response: requests.Response, jsonSchemaPaths: dict):
        self._response = response
        self._jsonDict = json.loads(response.text)
        self._transformedJsonDict = json.loads(response.text)
        self._transformSchema(jsonSchemaPaths)

    def __getitem__(self, key):
        return self._transformedJsonDict[key]

    @property
    def status(self):
        return self._response.status_code

    def transform(self, transformFn):
        return transformFn(self._jsonDict)

    def _transformSchema(self, jsonSchemaPaths):
        code = self._response.status_code
        schemaPathsForCode = jsonSchemaPaths.get(code, {})
        for (pathList, schemaClass) in schemaPathsForCode.items():
            dictToModify = self._transformedJsonDict
            validPathsList = [
                path
                for path in pathList
                if path != "$ref"
            ]
            for pathKey in validPathsList[:-1]:
                dictToModify = dictToModify[pathKey]
            lastPath = validPathsList[-1]
            dictToModify[lastPath] = schemaClass.fromSerialized(dictToModify[lastPath])
