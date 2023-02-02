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

    Implementation classes *must* provide data by calling all applicable data sets
    in the OpenAPI JSON object using these methods:
    - `_recordServer()`
    - `_recordMethod()`
    - `_recordResponseSchema()`
    - `_recordSchemaProperty()`
    """
    
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        self.__init_called = False
        self.__init__()
        if not self.__init_called:
            raise RuntimeError(f"Parser subclass {cls} did not call super().__init__()")
        return self

    def __init__(self):
        self.__init_called = True
        self.__servers = []
        self.__endpointsDict = dict()
        self.__schemaDict = dict()
        self._currSpecDict = None

    @abstractmethod
    def parse(self, openApiSpecDict: dict):
        assert type(openApiSpecDict) is dict
        self._currSpecDict = openApiSpecDict
        # subclasses should probably assert the openApiSpecDict['openapi'] version
        return # None, but call all relevant _record...() methods

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

    def _recordResponseSchema(self, method: 'Parser.Method', responseCodeStr, specKeyPathDescriptor, schemaClassRefStr):
        responseCodeInt = int(responseCodeStr)
        method._addSchemaToResponseJson(responseCodeInt, specKeyPathDescriptor, schemaClassRefStr)

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
            return f"<Parser.Endpoint {self.getPath()}>"

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
            self._responseSchema = dict()

        @property
        def name(self) -> str:
            return self._name

        @property
        def desc(self) -> str:
            return self._desc

        def addSchemaToResponseJson(self, responseCode: int, jsonPathTuple: tuple[str], schemaClassRefStr: str):
            if responseCode not in self._responseSchema:
                self._responseSchema[responseCode] = dict()
            responseJsonSchema = self._responseSchema[responseCode]
            responseJsonSchema[jsonPathTuple] = schemaClassRefStr

        def allSchemaInResponseJson(self) -> Iterable[tuple[int, tuple[str], str]]:
            for (responseCode, schemaPathMap) in self._responseSchema.items():
                for (schemaPath, schemaClassRefStr) in schemaPathMap.items():
                    yield (responseCode, schemaPath, schemaClassRefStr)


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

        serverList = jsonDict['servers']
        for (server, idx) in zip(serverList, range(len(serverList))):
            name = server['description'] or f"NO_NAME_FOUND_{idx + 1}"
            url = server['url']
            server = Parser.Server(name, url, f"Your description for '{name}' here")
            self._recordServer(server)
        
        for (schemaName, schemaData) in jsonDict['components']['schemas'].items():
            for (propName, propData) in schemaData['properties'].items():
                prop = Parser.SchemaProperty(propName, propData.get('description', ""))
                self._recordSchemaProperty(schemaName, schemaData.get('description', ""), prop)

        for (pathUrl, path) in jsonDict['paths'].items():
            for (method, methodData) in path.items():
                isActuallyMethod = method != 'parameters'
                if isActuallyMethod:
                    method = Parser.Method(method, self._genEndpointDesc(methodData))
                    self._recordMethod(pathUrl, method)

                    for (responseCode, responseData) in methodData['responses'].items():
                        def scanResponseDataWithContext(jsonKeyPath, jsonValue, jsonDict):
                            self._scanResponseData(jsonKeyPath, jsonValue, jsonDict, method, responseCode)
                        self._scanOpenApiObjectLayer(tuple(), responseData, jsonDict, scanResponseDataWithContext)

    def _scanOpenApiObjectLayer(self, jsonKeyPath, currObject, jsonDict, callbackForEachKey):
        isRef = len(jsonKeyPath) > 0 and jsonKeyPath[-1] == "$ref"
        if isRef:
            refPathList = currObject.split("/")
            refPathList_skippingHash = refPathList[1:]
            nextObject = jsonDict
            for pathKey in refPathList_skippingHash:
                nextObject = nextObject[pathKey]
            refType = refPathList[2]
            if refType == "schemas":
                nextObject = nextObject['properties']
            elif refType == "responses":
                # TODO: what if it isn't a ref?
                #       (breaks for GET /chats/{chat_id}/memberships)
                nextObject = nextObject \
                    .get('content', {}) \
                    .get('application/json', {}) \
                    .get('schema', {}) \
                    .get('properties')
                if nextObject is None:
                    return
            else:
                raise AssertionError("scanning api object revealed an unconsidered $ref type")
        else:
            nextObject = currObject
        
        if type(nextObject) in (dict, list):
            if type(nextObject) is dict:
                nextObjectIter = nextObject.items()
            else:
                nextObjectIter = enumerate(nextObject)
            for (jsonKey, jsonValue) in nextObjectIter:
                nextJsonKeyPath = jsonKeyPath + (jsonKey,)
                callbackForEachKey(nextJsonKeyPath, jsonValue, jsonDict)

    def _scanResponseData(self, jsonKeyPath, jsonValue, jsonDict, method, responseCode):
        lastJsonKey = jsonKeyPath[-1]
        if lastJsonKey == '$ref':
            refPathList = jsonValue.split("/")
            refType = refPathList[2]
            if refType == "schemas":
                schemaClassRefStr = refPathList[-1]
                self._recordResponseSchema(method, responseCode, jsonKeyPath, schemaClassRefStr)
                return
        
        def scanResponseDataWithContext(jsonKeyPath, jsonValue, jsonDict):
            self._scanResponseData(jsonKeyPath, jsonValue, jsonDict, method, responseCode)
        self._scanOpenApiObjectLayer(jsonKeyPath, jsonValue, jsonDict, scanResponseDataWithContext)

    def _genEndpointDesc(self, methodData):
        summary = methodData['summary']
        wrappedDesc = methodData['description']
        return f"{summary}\n\n{wrappedDesc}"
