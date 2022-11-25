from abc import ABC, abstractmethod, abstractclassmethod
import json

class Endpoint(ABC):
    @abstractmethod
    def __new__(cls, endpointPathValue):
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
    def __new__(cls, NOT_EXPRESSION_ENDPOINT):
        raise RuntimeError("FixedEndpoints cannot be invoked")

class VariableEndpoint(Endpoint, ABC):
    def __new__(cls, NOT_EXPRESSION_ENDPOINT):
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

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self.__init__(*args, **kwargs)
        if not '_Schema__initted' in self.__dict__ or not self.__initted:
            raise TypeError("Child of Schema did not call Schema.__init__()")
        return self

    def __init__(self):
        self._filter = dict()
        self.__initted = True
    
    def __eq__(self, other):
        return type(self) is type(other) and self.serialize(ignoreFilter=True) == other.serialize(ignoreFilter=True)
    
    def serialize(self, ignoreFilter=False) -> dict:
        serialDict = self._serialize()
        shouldFilter = not ignoreFilter and len(self._filter) > 0
        if shouldFilter:
            return {
                key: val
                for (key, val) in serialDict.items()
                if key in self._filter
            }
        else:
            return serialDict

    def serialFilter(self, *paramsToUse):
        self._filter = paramsToUse

    @abstractmethod
    def _serialize(self):
        return # a serialized dict of self

    @classmethod
    def fromSerialized(cls, jsonDict: dict):
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
