import re
from typing import Iterable

from .files import _readOpenAPIFile, _createFileFromRoot
from .parser import Parser


def generateAPI(ParserClass: Parser, openApiFileLocation: str):
    """Generates the api.py file given a parser and API spec-file location"""
    if not isinstance(type(ParserClass), type) or not issubclass(ParserClass, Parser):
        raise TypeError("generateAPI() requires ParserClass to be a reference to some subclass of Parser, \
            specifically the Parser for the version of spec-file you're using")

    jsonDict = _readOpenAPIFile(openApiFileLocation)

    parser = ParserClass()
    parser.parse(jsonDict)
    with _createFileFromRoot("api.py") as apiFile:
        writer = _EndpointWriter(apiFile)
        writer.writeServers(parser.servers)
        writer.writeEndpoints(parser.endpoints)
        writer.writeSchema(parser.schema)


_imports = """\
from pyblitz import *
from pyblitz.http import *\
"""

_registerServerTemplate = """\
registerServer("{name}", "{url}", "{desc}")\
"""

_endpointGlobals = """\
#############
# ENDPOINTS #
#############

# endpoint base classes are located in the `common` module\
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

_variableEndpointTemplate = """\
class {name}(VariableEndpoint):
    @classmethod
    def _parentEndpoint(cls):
        return {parentRef}
    @classmethod
    def _urlName(cls):
        return str(pathValue)\
    {methods}{childClasses}\
"""

# renaming `pathValueName` allows __new__() calls to show actual argument names
# while still being able to reference a consistent `pathValue` variable name
# from the inner VariableEndpoint class
_expressionEndpointTemplate = """\
class {name}(ExpressionEndpoint):
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

# schema base classes are located in the `common` module\
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
    """Converts all Parser.Endpoints to classes (via string templates) and writes them to an api.py file

    Construct with a file (or anything with a .write() method), then write in any order:
    ```
        writer = _EndpointWriter(file)
        writer.writeServers(parser.servers)
        writer.writeEndpoints(parser.endpoints)
        writer.writeSchema(parser.schema)
    ```
    """

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

    def writeServers(self, servers: Iterable[Parser.Server]):
        registerFnsCode = self._classSep + "\n".join(
            serverRegisterCode
            for server in servers
            for serverRegisterCode in [_registerServerTemplate.format(name=server.name, url=server.url, desc=server.desc)]
        )
        self._file.write(registerFnsCode + self._classSep)

    def writeEndpoints(self, rootEndpoints: Iterable[Parser.Endpoint]):
        self._file.write(_endpointGlobals)
        self._file.write(self._genEndpoints(rootEndpoints) + self._classSep)

    def writeSchema(self, schema: Iterable[Parser.Schema]):
        self._file.write(_schemaGlobals)
        self._file.write(self._genSchema(schema) + self._classSep)

    def _genEndpoints(self, endpoints: Iterable[Parser.Endpoint]) -> str:
        return "".join(
            self._classSep + endpointCode
            for endpoint in endpoints
            for endpointCode in [self._genEndpointAndChildren(endpoint)]
        )

    def _genEndpointAndChildren(self, endpoint: Parser.Endpoint) -> str:
        if self._isExpressionEndpoint(endpoint):
            return self._genExpressionEndpointAndChildren(endpoint)
        else:
            return self._genFixedEndpointAndChildren(endpoint)

    def _genFixedEndpointAndChildren(self, endpoint: Parser.Endpoint) -> str:
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

        parentRef = self._genParentsFromExprAncestorStr(endpoint)

        return _fixedEndpointTemplate.format(
            name=endpoint.className,
            parentRef=parentRef,
            urlNameStr="'{}'".format(endpoint.pathName),
            methods=endpointMethodStrs,
            childClasses=childClassesCode,
        )

    def _genExpressionEndpointAndChildren(self, endpoint: Parser.Endpoint) -> str:
        nonVarChildEndpoints = list(endpoint.children)
        varEndpointChildren = [
            child for child in nonVarChildEndpoints if self._isVariableEndpoint(child)]
        assert len(varEndpointChildren) == 1
        varEndpointChild = varEndpointChildren[0]
        nonVarChildEndpoints.pop(nonVarChildEndpoints.index(varEndpointChild))

        varEndpointCode = self._indent(self._genVariableEndpointAndChildren(
            varEndpointChild), 2) + self._unindentClassSep
        varEndpointName = re.findall(
            "class ([^()]*)(\(.*\))?:", varEndpointCode)[0][0]

        parentRef = self._genParentsFromExprAncestorStr(endpoint)

        # TODO: this code is copied; probably should be shared somehow
        childClassesCode = self._indent(
            self._genEndpoints(nonVarChildEndpoints))

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

        return _expressionEndpointTemplate.format(
            name=endpoint.className,
            parentRef=parentRef,
            urlNameStr="'{}'".format(endpoint.pathName),
            pathValueName=varEndpointName,
            hardenedClass=varEndpointCode,
            hardenedClassName=varEndpointName,
            methodSep=self._methodSep,
            methods=endpointMethodStrs,
            childClasses=childClassesCode,
        )

    def _genVariableEndpointAndChildren(self, endpoint: Parser.Endpoint) -> str:
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

        parentRef = self._genParentsFromExprAncestorStr(endpoint)

        return _variableEndpointTemplate.format(
            name=endpoint.className,
            parentRef=parentRef,
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

    def _indent(self, code: str, indentLevel: int = 1) -> str:
        return code.replace("\n", "\n" + self._indentStr * indentLevel)

    def _isExpressionEndpoint(self, endpoint: Parser.Endpoint) -> bool:
        for child in endpoint.children:
            if self._isVariableEndpoint(child):
                return True
        return False

    def _isVariableEndpoint(self, childEndpoint: Parser.Endpoint) -> bool:
        return (childEndpoint.pathName[0], childEndpoint.pathName[-1]) == ("{", "}")

    def _parentsUpToExprEndpoint(self, endpoint: Parser.Endpoint) -> Iterable[Parser.Endpoint]:
        currEndpoint = endpoint.parent
        # even if it is; we want to yield immediate expr endpoint parents for var endpoints
        currIsExprEndpoint = False
        while currEndpoint is not None and not currIsExprEndpoint:
            yield currEndpoint
            currIsExprEndpoint = self._isVariableEndpoint(currEndpoint)
            currEndpoint = currEndpoint.parent

    def _genParentsFromExprAncestorStr(self, endpoint: Parser.Endpoint) -> str:
        ancestry = ".".join(parent.className for parent in reversed(
            list(self._parentsUpToExprEndpoint(endpoint))))
        if ancestry == "":
            ancestry = "None"
        return ancestry
