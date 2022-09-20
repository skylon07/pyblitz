from abc import ABC, abstractmethod, abstractclassmethod
import json
import requests

class Endpoint(ABC):
    @abstractmethod
    def __new__(cls, *args, **kwargs):
        return # an Endpoint subclass

    @abstractclassmethod
    def _parentEndpoint(cls):
        return # the reference to this class' outer Endpoint class
    
    @abstractclassmethod
    def _urlName(cls):
        return # the endpoint's name as it would appear in the api url path

    @classmethod
    def url(cls):
        urlNames = list(cls._urlNamesFromLeaf())
        return "/" + "/".join(reversed(urlNames))

    @classmethod
    def _urlNamesFromLeaf(cls):
        currEndpoint = cls
        while currEndpoint is not None:
            yield currEndpoint._urlName()
            currEndpoint = currEndpoint._parentEndpoint()

class FixedEndpoint(Endpoint, ABC):
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("FixedEndpoints cannot be invoked")

class VariableEndpoint(Endpoint, ABC):
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("VariableEndpoints cannot be invoked")

class ExpressionEndpoint(Endpoint, ABC):
    @abstractmethod
    def __new__(cls, pathValue):
        return # a VariableEndpoint class

class Schema(ABC):
    # NoProp != None since that could be an expected parameter value
    class NoProp:
        def __repr__(self):
            return str(self)
        def __str__(self):
            return "<NoProp>"
    NoProp = NoProp()
    
    @abstractmethod
    def serialize(self):
        return # a serialized dict of self

    @classmethod
    def fromResponse(cls, response):
        assert type(response) is requests.Response
        jsonDict = json.loads(response.text)
        if len(jsonDict.keys()) == 1 and 'data' in jsonDict:
            jsonDict = jsonDict['data']
        
        self = cls()
        self._loadJsonDict(jsonDict)
        return self

    @abstractmethod
    def _loadJsonDict(self, jsonDict):
        return # None, but load the jsonDict into class properties

def _convertDashesToCamelCase(string: str):
    strList = string.split("-")
    firstStr = strList.pop(0)
    return firstStr + "".join(
        _capitalize(strAfterDash)
        for strAfterDash in strList
    )

def _capitalize(string: str):
    return string[0].upper() + string[1:]
