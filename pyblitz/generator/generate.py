import re
from typing import Iterable

from .files import readOpenAPIFile, createFileFromRoot
from .parser import Parser

def generateAPI(ParserClass, fileLocation):
    assert issubclass(ParserClass, Parser)
    
    jsonDict = readOpenAPIFile(fileLocation)

    parser = ParserClass()
    parser.parse(jsonDict)
    with createFileFromRoot("api.py") as apiFile:
        writer = _EndpointWriter(apiFile)
        writer.writeServers(parser.servers)
        writer.writeEndpoints(parser.endpoints)
        writer.writeSchema(parser.schema)


_imports = """\
from abc import ABC, abstractmethod, abstractclassmethod
import json
import requests

from .http import *

"""

_registerServerTemplate = """\
registerServer("{name}", "{url}")\
"""

_endpointGlobals = """\
#############
# ENDPOINTS #
#############

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
    @abstractmethod
    def __new__(cls, pathValue):
        return # an Endpoint class hardened with the pathValue
"""

# as a general rule of thumb, each template should not start or
# end with whitespace; template variables also should NOT include
# newlines; think "if this variable wasn't here, do I want a newline?"
_fixedEndpointTemplate = """\
class {name}(FixedEndpoint):
    @classmethod
    def _parentEndpoint(cls):
        return {parentRef}
    @classmethod
    def _urlName(cls):
        return {urlNameStr}\
    {methods}{childClasses}\
"""

# renaming `pathValueName` allows __new__() calls to show actual argument names
# while still being able to reference a consistent `pathValue` variable name
# from the inner hardened class
_variableEndpointTemplate = """\
class {name}(VariableEndpoint):
    @classmethod
    def _parentEndpoint(cls):
        return {parentRef}
    def __new__(cls, {pathValueName}):
        pathValue = {pathValueName}
        {hardenedClass}\
        return {hardenedClassName}\
    {methodSep}\
    @classmethod
    def _urlName(cls):
        return {urlNameStr}\
    {methods}{childClasses}\
"""

_endpointMethodTemplate_noData = """\
def {method}(cls, *args, headers=dict(), data=None, **params):
    \"""{desc}\"""
    return {method}(cls, *args, headers=headers, data=data, **params)\
"""

_endpointMethodTemplate_full = """\
@classmethod
def {method}(cls, data, *args, headers=dict(), **params):
    \"""{desc}\"""
    return {method}(cls, data, *args, headers=headers, **params)\
"""

_schemaGlobals = """\
##########
# SCHEMA #
##########

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
"""

_schemaTemplate = """\
class {name}(Schema):
    \"""{desc}\"""
    _propNames = {propDefNames}\
    {methodSep}\
    def __init__(self):
        {propDefs}\
    {methodSep}\
    def serialize(self):
        serialDict = {{
            propName: propVal
            for propName in self._propNames
            for propVal in [self.__dict__[propName]]
            if propVal is not Schema.NoProp
        }}
        return serialDict\
    {methodSep}\
    def _loadJsonDict(self, jsonDict):
        for (propName, propVal) in jsonDict.items():
            assert propName in self._propNames, "Unknown property '{{}}' found when loading dict (are you sure it's the right type?)".format(propName)
            self.__dict__[propName] = propVal\
"""

_propTemplate = """\
self.{name} = Schema.NoProp
\"""{desc}\"""\
"""


class _EndpointWriter:
    # what "one indent" means; if you change this, make sure to change
    # the templates too
    _indentStr = "    "
    # "seps" control newline separation in different cases; each of
    # these should always contain at least one newline, or else you'll
    # generate syntax errors (one newline = "squished mode"; try it!)
    _methodSep = "\n\n"
    _classSep = "\n\n\n"
    _unindentClassSep = "\n\n"

    def __init__(self, file):
        self._file = file
        self._file.write(_imports)

    def writeServers(self, servers):
        registerFnsCode = "\n".join(
            serverRegisterCode
            for server in servers
            for serverRegisterCode in [_registerServerTemplate.format(name=server.name, url=server.url)]
        )
        self._file.write(registerFnsCode + self._classSep)

    def writeEndpoints(self, rootEndpoints):
        self._file.write(_endpointGlobals)
        self._file.write(self._genEndpoints(rootEndpoints) + self._classSep)

    def writeSchema(self, schema):
        self._file.write(_schemaGlobals)
        self._file.write(self._genSchema(schema) + self._classSep)

    def _genEndpoints(self, endpoints: Iterable[Parser.Endpoint]) -> str:
        return "".join(
            self._classSep + endpointCode
            for endpoint in endpoints
            for endpointCode in [self._genEndpointAndChildren(endpoint)]
        )

    def _genEndpointAndChildren(self, endpoint: Parser.Endpoint) -> str:
        if self._isVaraibleEndpoint(endpoint):
            return self._genVariableEndpointAndChildren(endpoint)
        else:
            return self._genFixedEndpointAndChildren(endpoint)

    def _genFixedEndpointAndChildren(self, endpoint: Parser.Endpoint, fromVariableEndpoint=False) -> str:
        childClassesCode = self._indent(self._genEndpoints(endpoint.children))

        endpointMethodStrs = self._indent("".join(
            self._methodSep + methodStr
            for method in endpoint.methods
            for methodTemplate in [
                _endpointMethodTemplate_noData if method.name in ("get", "delete")
                else _endpointMethodTemplate_full
            ]
            for methodStr in [methodTemplate.format(
                method=method.name.upper(),
                desc=method.desc,
            )]
        ))

        parentRef = self._genFixedParentAncestryStrFromRoot(endpoint)

        if not fromVariableEndpoint:
            return _fixedEndpointTemplate.format(
                name=endpoint.className,
                parentRef=parentRef,
                urlNameStr="'{}'".format(endpoint.pathName),
                methods=endpointMethodStrs,
                childClasses=childClassesCode,
            )
        else:
            return _fixedEndpointTemplate.format(
                name=endpoint.className,
                parentRef=parentRef,
                urlNameStr="str(pathValue)",
                methods=endpointMethodStrs,
                childClasses=childClassesCode,
            )

    def _genVariableEndpointAndChildren(self, endpoint: Parser.Endpoint) -> str:
        fixedChildren = list(endpoint.children)
        varEndpointChildren = [child for child in fixedChildren if self._isParentVariableEndpoint(child)]
        assert len(varEndpointChildren) == 1
        varEndpointChild = varEndpointChildren[0]
        fixedChildren.pop(fixedChildren.index(varEndpointChild))

        hardenedEndpointCode = self._indent(self._genFixedEndpointAndChildren(varEndpointChild, fromVariableEndpoint=True), 2) + self._unindentClassSep
        hardenedEndpointName = re.findall("class ([^()]*)(\(.*\))?:", hardenedEndpointCode)[0][0]

        parentRef = self._genFixedParentAncestryStrFromRoot(endpoint)

        # TODO: this code is copied; probably should be shared somehow
        childClassesCode = self._indent(self._genEndpoints(fixedChildren))

        endpointMethodStrs = self._indent("".join(
            self._methodSep + methodStr
            for method in endpoint.methods
            for methodTemplate in [
                _endpointMethodTemplate_noData if method.name in ("get", "delete")
                else _endpointMethodTemplate_full
            ]
            for methodStr in [methodTemplate.format(
                method=method.name.upper(),
                desc=method.desc,
            )]
        ))

        return _variableEndpointTemplate.format(
            name=endpoint.className,
            parentRef=parentRef,
            urlNameStr="'{}'".format(endpoint.pathName),
            pathValueName=hardenedEndpointName,
            hardenedClass=hardenedEndpointCode,
            hardenedClassName=hardenedEndpointName,
            methodSep=self._methodSep,
            methods=endpointMethodStrs,
            childClasses=childClassesCode,
        )

    def _genSchema(self, schema: Iterable[Parser.Schema]) -> str:
        return "".join(
            self._classSep + schemaCode
            for model in schema
            for schemaCode in [self._genSchemaModel(model)]
        )

    def _genSchemaModel(self, model: Parser.Schema) -> str:
        propDefsStr = self._indent("\n".join(
            propCode
            for prop in model.props
            for propCode in [self._genProp(prop)]
        ), 2)

        propDefNames = {
            prop.name
            for prop in model.props
        }

        return _schemaTemplate.format(
            name=model.name,
            desc=model.desc,
            propDefs=propDefsStr,
            propDefNames=propDefNames,
            methodSep=self._methodSep,
        )

    def _genProp(self, prop: Parser.SchemaProperty) -> str:
        return _propTemplate.format(
            name=prop.name,
            desc=prop.desc,
        )

    def _indent(self, code: str, indentLevel: int=1) -> str:
        return code.replace("\n", "\n" + self._indentStr * indentLevel)

    def _isVaraibleEndpoint(self, endpoint: Parser.Endpoint) -> bool:
        for child in endpoint.children:
            if self._isParentVariableEndpoint(child):
                return True
        return False

    def _isParentVariableEndpoint(self, childEndpoint: Parser.Endpoint) -> bool:
        return (childEndpoint.pathName[0], childEndpoint.pathName[-1]) == ("{", "}")
    
    def _genFixedParentAncestryFromLeaf(self, endpoint: Parser.Endpoint) -> Iterable[Parser.Endpoint]:
        currEndpoint = endpoint.parent
        isCurrEndpointVariable = False # even if it is, we want to yield the first reference regardless
        while currEndpoint is not None and not isCurrEndpointVariable:
            yield currEndpoint
            isCurrEndpointVariable = self._isParentVariableEndpoint(currEndpoint)
            currEndpoint = currEndpoint.parent

    def _genFixedParentAncestryStrFromRoot(self, endpoint: Parser.Endpoint) -> str:
        ancestry = ".".join(parent.className for parent in reversed(list(self._genFixedParentAncestryFromLeaf(endpoint))))
        if ancestry == "":
            ancestry = "None"
        return ancestry
