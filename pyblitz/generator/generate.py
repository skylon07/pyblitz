import re
from typing import Iterable

from .files import _readOpenAPIFile, _createApiFile
from .parser import Parser


def generateAPI(ParserClass: Parser, openApiFilePath: str, apiOutputPath: str):
    """Generates the api.py file given a parser and API spec-file location"""
    if not isinstance(type(ParserClass), type) or not issubclass(ParserClass, Parser):
        raise TypeError("generateAPI() requires ParserClass to be a reference to some subclass of Parser, \
            specifically the Parser for the version of spec-file you're using")

    if apiOutputPath[-3:] != ".py":
        raise ValueError("apiOutputPath must point to a '.py' file")

    jsonDict = _readOpenAPIFile(openApiFilePath)

    parser = ParserClass()
    parser.parse(jsonDict)
    with _createApiFile(apiOutputPath) as apiFile:
        writer = _EndpointWriter(apiFile)
        writer.writeServers(parser.servers)
        writer.writeEndpoints(parser.endpoints)
        writer.writeSchema(parser.schema)


_imports = """\
from typing import Any
import pyblitz

http = pyblitz.http
Schema = pyblitz.common.Schema\
"""

_registerServerTemplate = """\
pyblitz.http.registerServer("{name}", "{url}", "{desc}")\
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
class {name}(pyblitz.FixedEndpoint):
    @classmethod
    def _parentEndpoint(cls):
        return {parentRef}
    @classmethod
    def _urlName(cls):
        return {urlNameStr}\
    {schemaInResponseGetters}{methods}{childClasses}\
"""

_variableEndpointTemplate = """\
class {name}(pyblitz.VariableEndpoint):
    @classmethod
    def _parentEndpoint(cls):
        return {parentRef}
    @classmethod
    def _urlName(cls):
        return str(pathValue)\
    {schemaInResponseGetters}{methods}{childClasses}\
"""

# renaming `pathValueName` allows __new__() calls to show actual argument names
# while still being able to reference a consistent `pathValue` variable name
# from the inner VariableEndpoint class
_expressionEndpointTemplate = """\
class {name}(pyblitz.ExpressionEndpoint):
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
    {schemaInResponseGetters}{methods}{childClasses}\
"""

_endpointMethodTemplate_noData = """\
@classmethod
def {method}(cls, *args, headers=dict(), data=None, **params) -> pyblitz.http.Response:
    \"""{desc}\"""
    return pyblitz.http.{method}(cls, *args, headers=headers, data=data, **params)\
"""

_endpointMethodTemplate_full = """\
@classmethod
def {method}(cls, data, *args, headers=dict(), **params) -> pyblitz.http.Response:
    \"""{desc}\"""
    return pyblitz.http.{method}(cls, data, *args, headers=headers, **params)\
"""

_endpointSchemaInResponseGettersTemplate = """\
@classmethod
def _schemaInDeleteResponseJson(cls):
    return {schemaInResponseDelete}
@classmethod
def _schemaInGetResponseJson(cls):
    return {schemaInResponseGet}
@classmethod
def _schemaInPatchResponseJson(cls):
    return {schemaInResponsePatch}
@classmethod
def _schemaInPostResponseJson(cls):
    return {schemaInResponsePost}
@classmethod
def _schemaInPutResponseJson(cls):
    return {schemaInResponsePut}\
"""

_schemaGlobals = """\
##########
# SCHEMA #
##########

# schema base classes are located in the `common` module\
"""

_schemaTemplate = """\
class {name}(pyblitz.Schema):
    \"""{desc}\"""
    _propNames = {propDefNames}\
    {methodSep}\
    def __init__(self, {propDefsParams}):
        super().__init__()
        {propDefsAssignments}\
    {methodSep}\
    def _serialize(self):
        serialDict = {{
            propName: propVal
            for propName in self._propNames
            for propVal in [self.__dict__[propName]]
            if propVal is not pyblitz.Schema.NoProp
        }}
        return serialDict\
    {methodSep}\
    def _loadJsonDict(self, jsonDict):
        for (propName, propVal) in jsonDict.items():
            if propName not in self._propNames:
                raise KeyError(f"Unknown property '{{propName}}' found when loading Schema")
            self.__dict__[propName] = propVal\
"""

_propParamTemplate = """\
{name}: Any = pyblitz.Schema.NoProp, \
"""

_propAsssignmentTemplate = """\
self.{name} = {name}
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
                method=method.name,
                desc=method.desc,
            )]
        ))

        parentRef = self._genParentsFromExprAncestorStr(endpoint)

        schemaInResponseGetters = self._indent(self._methodSep + self._genSchemaInResponseGettersStr(endpoint))

        return _fixedEndpointTemplate.format(
            name=endpoint.className,
            parentRef=parentRef,
            urlNameStr=f"'{endpoint.pathName}'",
            methods=endpointMethodStrs,
            childClasses=childClassesCode,
            schemaInResponseGetters=schemaInResponseGetters,
        )

    def _genExpressionEndpointAndChildren(self, endpoint: Parser.Endpoint) -> str:
        nonVarChildEndpoints = list(endpoint.children)
        # TODO: what if the child is also an expression endpoint?
        varEndpointChildren = [
            child
            for child in nonVarChildEndpoints
            if self._isVariableEndpoint(child)
        ]
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
                method=method.name,
                desc=method.desc,
            )]
        ))

        schemaInResponseGetters = self._indent(self._methodSep + self._genSchemaInResponseGettersStr(endpoint))

        return _expressionEndpointTemplate.format(
            name=endpoint.className,
            parentRef=parentRef,
            urlNameStr=f"'{endpoint.pathName}'",
            pathValueName=varEndpointName,
            hardenedClass=varEndpointCode,
            hardenedClassName=varEndpointName,
            methodSep=self._methodSep,
            methods=endpointMethodStrs,
            childClasses=childClassesCode,
            schemaInResponseGetters=schemaInResponseGetters,
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
                method=method.name,
                desc=method.desc,
            )]
        ))

        parentRef = self._genParentsFromExprAncestorStr(endpoint)

        schemaInResponseGetters = self._indent(self._methodSep + self._genSchemaInResponseGettersStr(endpoint))

        return _variableEndpointTemplate.format(
            name=endpoint.className,
            parentRef=parentRef,
            methods=endpointMethodStrs,
            childClasses=childClassesCode,
            schemaInResponseGetters=schemaInResponseGetters,
        )

    def _genSchemaInResponseGettersStr(self, endpoint: Parser.Endpoint):
        methodGet = None
        methodDelete = None
        methodPatch = None
        methodPost = None
        methodPut = None
        for method in endpoint.methods:
            if method.name == "get":
                methodGet = method
            elif method.name == "delete":
                methodDelete = method
            elif method.name == "patch":
                methodPatch = method
            elif method.name == "post":
                methodPost = method
            elif method.name == "put":
                methodPut = method

        return _endpointSchemaInResponseGettersTemplate.format(
            schemaInResponseGet=self._genSchemaInResponseStr(methodGet),
            schemaInResponseDelete=self._genSchemaInResponseStr(methodDelete),
            schemaInResponsePatch=self._genSchemaInResponseStr(methodPatch),
            schemaInResponsePost=self._genSchemaInResponseStr(methodPost),
            schemaInResponsePut=self._genSchemaInResponseStr(methodPut),
        )

    def _genSchemaInResponseStr(self, method: Parser.Method):
        if method is not None:
            schemaPathsMap = dict()
            for (responseCode, jsonPathKeys, schemaClassRefStr) in method.allSchemaInResponseJson():
                if responseCode not in schemaPathsMap:
                    schemaPathsMap[responseCode] = dict()
                schemaPathsMapForCode = schemaPathsMap[responseCode]
                schemaPathsMapForCode[jsonPathKeys] = f"<{schemaClassRefStr}>"
            schemaInResponseStr = re.sub(r"'\<(?P<class>.*?)\>'", r"\g<class>", f"{schemaPathsMap}")
            return schemaInResponseStr
        else:
            return "{}"


    def _genSchema(self, schema: Iterable[Parser.Schema]) -> str:
        return "".join(
            self._classSep + schemaCode
            for model in schema
            for schemaCode in [self._genSchemaModel(model)]
        )

    def _genSchemaModel(self, model: Parser.Schema) -> str:
        propDefsParamsStr = self._indent("\n".join(
            propCode
            for prop in model.props
            for propCode in [_propParamTemplate.format(name=prop.name, desc=prop.desc)]
        ), 2)
        propDefsAssignmentsStr = self._indent("\n".join(
            propCode
            for prop in model.props
            for propCode in [_propAsssignmentTemplate.format(name=prop.name, desc=prop.desc)]
        ), 2)

        propDefNames = {
            prop.name
            for prop in model.props
        }

        return _schemaTemplate.format(
            name=model.name,
            desc=model.desc,
            propDefsParams=propDefsParamsStr,
            propDefsAssignments=propDefsAssignmentsStr,
            propDefNames=propDefNames,
            methodSep=self._methodSep,
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
