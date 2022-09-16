from abc import ABC, abstractmethod
from typing import Iterable

from ..common import _convertDashesToCamelCase


class ParseError(Exception):
    pass # class intentionally left blank


class Parser(ABC):
    """The base class for all Parsers, providing common functionality and data classes
    
    A Parser instance's main use is to `parse(jsonDict)` a dictionary generated from json.
    Once parsed, the Parser instance provides several properties:
    - servers -- a list of found Parser.Servers
    - endpoints -- a list of found Parser.Endpoints
    - schema -- a list of found Parser.Schema
    """
    
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        self.__init_called = False
        self.__init__()
        if not self.__init_called:
            raise RuntimeError("Parser subclass {} did not call super().__init__()".format(cls))
        return self

    def __init__(self):
        self.__init_called = True
        self.__servers = []
        self.__endpointsDict = dict()
        self.__schemaDict = dict()

    @abstractmethod
    def parse(self, jsonDict):
        assert type(jsonDict) is dict
        # also should probably assert the jsonDict['openapi'] version
        return # None, but call _recordMethod() and all relevant on...() methods

    @property
    def servers(self):
        return self.__servers

    @property
    def endpoints(self):
        return self.__endpointsDict.values()

    @property
    def schema(self):
        return self.__schemaDict.values()

    def _recordServer(self, server):
        self.__servers.append(server)

    def _recordMethod(self, pathUrl, method):
        assert type(pathUrl) is str
        assert type(method) is Parser.Method

        pathsSplit = pathUrl.split("/")
        if pathsSplit[0] == "":
            pathsSplit.pop(0)
        endpoint = None
        for childName in pathsSplit:
            if endpoint is None:
                if childName not in self.__endpointsDict:
                    childEndpoint = Parser.Endpoint(childName)
                    self.__endpointsDict[childName] = childEndpoint
                childEndpoint = self.__endpointsDict[childName]
            else:
                if not endpoint.hasChild(childName):
                    childEndpoint = Parser.Endpoint(childName, endpoint)
                childEndpoint = endpoint.getChildFromName(childName)
            endpoint = childEndpoint
        endpoint.addMethod(method)

    def _recordSchemaProperty(self, schemaName, schemaDesc, prop):
        assert type(schemaName) is str
        assert type(schemaDesc) is str
        assert type(prop) is Parser.SchemaProperty

        if schemaName not in self.__schemaDict:
            schema = Parser.Schema(schemaName, schemaDesc)
            self.__schemaDict[schemaName] = schema
        schema = self.__schemaDict[schemaName]
        schema.addProp(prop)


    class Server:
        """A data class representing Server data for the parser"""

        def __init__(self, name: str, url: str, desc: str):
            self._name = name
            self._url = url if url[-1] != "/" else url[:-1]
            self._desc = desc

        @property
        def name(self) -> str:
            return self._name

        @property
        def url(self) -> str:
            return self._url

        @property
        def desc(self) -> str:
            return self._desc


    class Endpoint:
        """A data class representing Endpoint data for the parser"""

        def __init__(self, pathName: str, parent: 'Parser.Endpoint'=None):
            assert type(pathName) is str
            if parent is not None:
                assert type(parent) is Parser.Endpoint
            
            self._pathName = pathName
            self._className = None
            self._parent = None
            self._lastParentOnPathCheck = None
            self._methodsDict = dict()
            self._childrenDict = dict()
            self._path = None

            if parent is not None:
                parent.addChild(self)

        def __repr__(self):
            return "<Parser.Endpoint {}>".format(self.getPath())

        @property
        def pathName(self) -> str:
            return self._pathName

        @property
        def className(self) -> str:
            if self._className is None:
                nameNoBraces = self._pathName[1:-1] if self._pathName[0] == "{" else self._pathName
                casedName = _convertDashesToCamelCase(nameNoBraces)
                self._className = casedName
            return self._className

        @property
        def parent(self) -> 'Parser.Endpoint':
            return self._parent

        def getPath(self) -> str:
            if self._path is None or self._lastParentOnPathCheck is not self._parent:
                parentPath = self._parent.getPath() if self._parent is not None else ""
                self._path = parentPath + "/" + self._pathName
                self._lastParentOnPathCheck = self._parent
            return self._path

        # CHILDREN ENDPOINTS

        @property
        def children(self) -> Iterable['Parser.Endpoint']:
            return self._childrenDict.values()

        def addChild(self, childEndpoint: 'Parser.Endpoint') -> None:
            assert type(childEndpoint) is Parser.Endpoint
            childEndpoint._parent = self
            self._childrenDict[childEndpoint.pathName] = childEndpoint

        def hasChild(self, childEndpointName: str) -> bool:
            return childEndpointName in self._childrenDict
        
        def getChildFromName(self, childEndpointName: str) -> 'Parser.Endpoint':
            return self._childrenDict[childEndpointName]

        # ASSOCIATED METHODS

        @property
        def methods(self) -> Iterable['Parser.Method']:
            return self._methodsDict.values()

        def addMethod(self, method: 'Parser.Method') -> None:
            assert type(method) is Parser.Method
            self._methodsDict[method.name] = method

        def hasMethod(self, methodName: str) -> bool:
            return methodName in self._methodsDict

        def getMethodFromName(self, methodName: str) -> 'Parser.Method':
            return self._methodsDict[methodName]


    class Method:
        """A data class representing Method data for the parser"""

        def __init__(self, name: str, desc: str):
            assert type(name) is str
            assert type(desc) is str

            self._name = name
            self._desc = desc

        @property
        def name(self) -> str:
            return self._name

        @property
        def desc(self) -> str:
            return self._desc


    class Schema:
        """A data class representing a Schema model for the parser"""

        def __init__(self, name: str, desc: str):
            assert type(name) is str
            assert type(desc) is str

            self._name = name
            self._desc = desc
            self._properties = dict()

        @property
        def name(self) -> str:
            return self._name

        @property
        def desc(self) -> str:
            return self._desc

        @property
        def props(self) -> Iterable['Parser.SchemaProperty']:
            return self._properties.values()

        def addProp(self, prop: 'Parser.SchemaProperty') -> None:
            assert type(prop) is Parser.SchemaProperty
            self._properties[prop.name] = prop

        def hasProp(self, propName: str) -> bool:
            return propName in self._properties

        def getPropFromName(self, propName: str) -> 'Parser.SchemaProperty':
            return self._properties[propName]


    class SchemaProperty:
        """A data class representing a SchemaProperty for the parser"""

        def __init__(self, name: str, desc: str):
            assert type(name) is str
            assert type(desc) is str

            self._name = name
            self._desc = desc

        @property
        def name(self) -> str:
            return self._name

        @property
        def desc(self) -> str:
            return self._desc


class Parser_3_1_0(Parser):
    def parse(self, jsonDict):
        assert type(jsonDict) is dict
        assert jsonDict['openapi'] == "3.1.0", \
            "Parser_3_1_0 is intended to only work with version 3.1.0 specifications"

        for server in jsonDict['servers']:
            desc = server['description']
            if desc == "Production":
                server = Parser.Server('prod', server['url'], desc)
            elif desc == "Development":
                server = Parser.Server('dev', server['url'], desc)
            else:
                raise ParseError("An invalid server type was received")
            self._recordServer(server)

        for (pathUrl, path) in jsonDict['paths'].items():
            for (method, methodData) in path.items():
                isActuallyMethod = method != 'parameters'
                if isActuallyMethod:
                    method = Parser.Method(method, self._genEndpointDesc(methodData))
                    self._recordMethod(pathUrl, method)

        for (schemaName, schemaData) in jsonDict['components']['schemas'].items():
            for (propName, propData) in schemaData['properties'].items():
                prop = Parser.SchemaProperty(propName, propData.get('description', ""))
                self._recordSchemaProperty(schemaName, schemaData.get('description', ""), prop)

    def _genEndpointDesc(self, methodData):
        summary = methodData['summary']
        wrappedDesc = methodData['description']
        return "{}\n\n{}".format(summary, wrappedDesc)
