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
Schema = pyblitz.common.Schema
NoProp = Schema.NoProp\
"""

def _useRegisterServerTemplate(*args, serverName, serverUrl, serverDesc):
    return f'pyblitz.http.registerServer("{serverName}", "{serverUrl}", "{serverDesc}")'

_endpointGlobals = """\
#############
# ENDPOINTS #
#############

# endpoint base classes are located in the `common` module\
"""

# as a general rule of thumb, each template should not start or
# end with whitespace; template variables also should NOT include
# newlines; think "if this variable wasn't here, do I want a newline?"
def _useFixedEndpointTemplate(*args, endpointName, parentRef, urlNameStr, schemaInResponseGettersCode, methodsCode, childClassesCode):
    return (
        f'class {endpointName}(pyblitz.FixedEndpoint):\n'
        f'    @classmethod\n'
        f'    def _parentEndpoint(cls):\n'
        f'        return {parentRef}\n'
        f'    @classmethod\n'
        f'    def _urlName(cls):\n'
        f'        return {urlNameStr}'
        f'    {schemaInResponseGettersCode}{methodsCode}{childClassesCode}'
    )

def _useVariableEndpointTemplate(*args, endpointName, parentRef, schemaInResponseGettersCode, methodsCode, childClassesCode):
    return (
        f'class {endpointName}(pyblitz.VariableEndpoint):\n'
        f'    @classmethod\n'
        f'    def _parentEndpoint(cls):\n'
        f'        return {parentRef}\n'
        f'    @classmethod\n'
        f'    def _urlName(cls):\n'
        f'        return str(pathValue)'
        f'    {schemaInResponseGettersCode}{methodsCode}{childClassesCode}'
    )

def _useExpressionEndpointTemplate(*args, endpointName, parentRef, pathValueName, hardenedClassCode, hardenedClassName, methodSep, urlNameStr, schemaInResponseGettersCode, methodsCode, childClassesCode):
    return (
        f'class {endpointName}(pyblitz.ExpressionEndpoint):\n'
        f'    @classmethod\n'
        f'    def _parentEndpoint(cls):\n'
        f'        return {parentRef}\n'
        f'    def __new__(cls, {pathValueName}):\n'
                  # renaming `pathValueName` here allows __new__() calls to show actual argument names while
                  # still being able to reference a consistent `pathValue` variable name from the inner class
        f'        pathValue = {pathValueName}\n'
        f'        {hardenedClassCode}'
        f'        return {hardenedClassName}'
        f'    {methodSep}'
        f'    @classmethod\n'
        f'    def _urlName(cls):\n'
        f'        return {urlNameStr}'
        f'    {schemaInResponseGettersCode}{methodsCode}{childClassesCode}'
    )

def _useEndpointMethod_noDataTemplate(*args, methodName, methodDesc):
    return (
        f'@classmethod\n'
        f'def {methodName}(cls, *args, headers = dict(), data = None, **params) -> pyblitz.http.Response:\n'
        f'    """{methodDesc}"""\n'
        f'    return pyblitz.http.{methodName}(cls, *args, headers = headers, data = data, **params)'
    )

def _useEndpointMethod_fullTemplate(*args, methodName, methodDesc):
    return (
        f'@classmethod\n'
        f'def {methodName}(cls, data, *args, headers=dict(), **params) -> pyblitz.http.Response:\n'
        f'    """{methodDesc}"""\n'
        f'    return pyblitz.http.{methodName}(cls, data, *args, headers=headers, **params)'
    )

def _useEndpointSchemaInResponseGettersTemplate(*args, schemaInResponseDelete, schemaInResponseGet, schemaInResponsePatch, schemaInResponsePost, schemaInResponsePut):
    return (
        f'@classmethod\n'
        f'def _schemaInDeleteResponseJson(cls):\n'
        f'    return {schemaInResponseDelete}\n'
        f'@classmethod\n'
        f'def _schemaInGetResponseJson(cls):\n'
        f'    return {schemaInResponseGet}\n'
        f'@classmethod\n'
        f'def _schemaInPatchResponseJson(cls):\n'
        f'    return {schemaInResponsePatch}\n'
        f'@classmethod\n'
        f'def _schemaInPostResponseJson(cls):\n'
        f'    return {schemaInResponsePost}\n'
        f'@classmethod\n'
        f'def _schemaInPutResponseJson(cls):\n'
        f'    return {schemaInResponsePut}'
    )

_schemaGlobals = """\
##########
# SCHEMA #
##########

# schema base classes are located in the `common` module\
"""

def _useSchemaTemplate(*args, schemaName, schemaDesc, propDefNames, methodSep, propDefsParams, propDefsAssignments):
    return (
        f'class {schemaName}(pyblitz.Schema):\n'
        f'    """{schemaDesc}"""\n'
        f'    _propNames = {propDefNames}'
        f'    {methodSep}'
        f'    def __init__(self, {propDefsParams}):\n'
        f'        super().__init__()\n'
        f'        {propDefsAssignments}'
        f'    {methodSep}'
        f'    def _serialize(self):\n'
        f'        serialDict = {{\n'
        f'            propName: propVal\n'
        f'            for propName in self._propNames\n'
        f'            for propVal in [self.__dict__[propName]]\n'
        f'            if propVal is not pyblitz.Schema.NoProp\n'
        f'        }}\n'
        f'        return serialDict'
        f'    {methodSep}'
        f'    def _loadJsonDict(self, jsonDict, looseChecking):\n'
        f'        for (propName, propVal) in jsonDict.items():\n'
        f'            if propName in self._propNames:\n'
        f'                self.__dict__[propName] = propVal\n'
        f'            elif not looseChecking:\n'
        f'                raise KeyError(f"Unknown property \'{{propName}}\' found when loading Schema")'
    )

def _usePropParamTemplate(*args, propName):
    return f'{propName}: Any = NoProp, '

def _usePropAssignmentTemplate(*args, propName, propDesc):
    return (
        f'self.{propName} = {propName}\n'
        f'"""{propDesc}"""'
    )


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
            for serverRegisterCode in [_useRegisterServerTemplate(
                serverName = server.name,
                serverUrl = server.url,
                serverDesc = server.desc,
            )]
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
            for methodTemplateFn in [
                _useEndpointMethod_noDataTemplate if method.name in ("get", "delete")
                else _useEndpointMethod_fullTemplate
            ]
            for methodStr in [methodTemplateFn(
                methodName = method.name,
                methodDesc = method.desc,
            )]
        ))

        parentRef = self._genParentsFromExprAncestorStr(endpoint)

        schemaInResponseGetters = self._indent(self._methodSep + self._genSchemaInResponseGettersStr(endpoint))

        return _useFixedEndpointTemplate(
            endpointName = endpoint.className,
            parentRef = parentRef,
            urlNameStr = f'"{endpoint.pathName}"',
            methodsCode = endpointMethodStrs,
            childClassesCode = childClassesCode,
            schemaInResponseGettersCode = schemaInResponseGetters,
        )

    def _genExpressionEndpointAndChildren(self, endpoint: Parser.Endpoint) -> str:
        nonVarChildEndpoints = list(endpoint.children)
        varEndpointChildren = [
            child
            for child in nonVarChildEndpoints
            if self._isVariableEndpoint(child)
        ]
        assert len(varEndpointChildren) == 1
        varEndpointChild = varEndpointChildren[0]
        # TODO: what if the child is also an expression endpoint?
        #       (probably need to add a _useVariableExpressionEndpointTemplate()
        #       that merges the two other templates)
        assert not self._isExpressionEndpoint(varEndpointChild), "expression endpoints cannot currently handle expression endpoint children"
        nonVarChildEndpoints.remove(varEndpointChild)

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
            for methodTemplateFn in [
                _useEndpointMethod_noDataTemplate if method.name in ("get", "delete")
                else _useEndpointMethod_fullTemplate
            ]
            for methodStr in [methodTemplateFn(
                methodName = method.name,
                methodDesc = method.desc,
            )]
        ))

        schemaInResponseGetters = self._indent(self._methodSep + self._genSchemaInResponseGettersStr(endpoint))

        return _useExpressionEndpointTemplate(
            endpointName = endpoint.className,
            parentRef = parentRef,
            urlNameStr = f"'{endpoint.pathName}'",
            pathValueName = varEndpointName,
            hardenedClassCode = varEndpointCode,
            hardenedClassName = varEndpointName,
            methodSep = self._methodSep,
            methodsCode = endpointMethodStrs,
            childClassesCode = childClassesCode,
            schemaInResponseGettersCode = schemaInResponseGetters,
        )

    def _genVariableEndpointAndChildren(self, endpoint: Parser.Endpoint) -> str:
        childClassesCode = self._indent(self._genEndpoints(endpoint.children))

        endpointMethodStrs = self._indent("".join(
            self._methodSep + methodStr
            for method in endpoint.methods
            for methodTemplateFn in [
                _useEndpointMethod_noDataTemplate if method.name in ("get", "delete")
                else _useEndpointMethod_fullTemplate
            ]
            for methodStr in [methodTemplateFn(
                methodName = method.name,
                methodDesc = method.desc,
            )]
        ))

        parentRef = self._genParentsFromExprAncestorStr(endpoint)

        schemaInResponseGetters = self._indent(self._methodSep + self._genSchemaInResponseGettersStr(endpoint))

        return _useVariableEndpointTemplate(
            endpointName = endpoint.className,
            parentRef = parentRef,
            methodsCode = endpointMethodStrs,
            childClassesCode = childClassesCode,
            schemaInResponseGettersCode = schemaInResponseGetters,
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

        return _useEndpointSchemaInResponseGettersTemplate(
            schemaInResponseGet = self._genSchemaInResponseStr(methodGet),
            schemaInResponseDelete = self._genSchemaInResponseStr(methodDelete),
            schemaInResponsePatch = self._genSchemaInResponseStr(methodPatch),
            schemaInResponsePost = self._genSchemaInResponseStr(methodPost),
            schemaInResponsePut = self._genSchemaInResponseStr(methodPut),
        )

    def _genSchemaInResponseStr(self, method: Parser.Method):
        if method is not None:
            schemaPathsMap = dict()
            for (responseCode, jsonPathKeys, schemaClassRefStr) in method.allSchemaInResponseJson():
                if responseCode not in schemaPathsMap:
                    schemaPathsMap[responseCode] = dict()
                schemaPathsMapForCode = schemaPathsMap[responseCode]
                schemaPathsMapForCode[jsonPathKeys] = f"<{schemaClassRefStr}>"
            # replaces "'<schemaClassName>'" --> "schemaClassName"
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
        propDefsParamsStr = self._indent("\n" + "\n".join(
            propCode
            for prop in model.props
            for propCode in [_usePropParamTemplate(
                propName = prop.name,
            )]
        ), 2) + self._indent("\n", 1)
        propDefsAssignmentsStr = self._indent("\n".join(
            propCode
            for prop in model.props
            for propCode in [_usePropAssignmentTemplate(
                propName = prop.name,
                propDesc = prop.desc,
            )]
        ), 2)

        propDefNames = {
            prop.name
            for prop in model.props
        }

        return _useSchemaTemplate(
            schemaName = model.name,
            schemaDesc = model.desc,
            propDefNames = propDefNames,
            propDefsParams = propDefsParamsStr,
            propDefsAssignments = propDefsAssignmentsStr,
            methodSep = self._methodSep,
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
