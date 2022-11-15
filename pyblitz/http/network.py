from requests import Session

from ..common import Endpoint
from .requests import Request
from .responses import Response


class _NetworkState:
    isAuthed = False
    activeServer = None
    servers = dict()
    session = Session()


def registerServer(name, url, desc=""):
    """Records data for a server that can later be activated by `setActiveServer(name)`"""
    if url[-1] == "/":
        url.pop()
    _NetworkState.servers[name] = url

def getServer(name):
    """Returns the stored url for a previously registered server"""
    return _NetworkState.servers[name]

def getServerNames():
    """Returns all previously registered server names"""
    return list(_NetworkState.servers.keys())

def setActiveServer(name):
    """Sets the active server to use for all future requests.
    
    This can be called any number of times at any point while your program is running.
    Requests will always be made to the server that was last activated by this function.
    """

    if name not in _NetworkState.servers:
        raise ValueError(f"Server '{name}' is not registered!")
    _NetworkState.activeServer = _NetworkState.servers[name]


def setAuth(token):
    """Sets the authentication token to use for all requests.
    
    This can be called any number of times at any point while your program is running.
    Requests will always use the token that was last recorded by this function.
    """

    _NetworkState.session.headers.update({
        "authorization": f"Bearer {token}",
    })
    _NetworkState.isAuthed = True


def _authenticated(fn):
    """A decorator that ensures calls made to an HTTP method are both authenticated and have a target server"""
    def authedFn(*args, **kwargs):
        if _NetworkState.activeServer is None:
            raise RuntimeError("Cannot make network requests until a server is chosen via pyblitz.http.setActiveServer()")
        if not _NetworkState.isAuthed:
            raise RuntimeError("Cannot make network requests until authentication is set with pyblitz.http.setAuth()")
        return fn(*args, **kwargs)
    return authedFn


@_authenticated
def DELETE(endpoint: Endpoint, headers=dict(), data=None, **params) -> Response:
    _checkIsEndpoint(endpoint)
    fullUrl = _NetworkState.activeServer + endpoint.url()
    request = Request.Delete(fullUrl)
    request.load(data, headers, params)
    httpResponse = request.send()
    return Response(httpResponse)

@_authenticated
def GET(endpoint: Endpoint, headers=dict(), data=None, **params) -> Response:
    _checkIsEndpoint(endpoint)
    fullUrl = _NetworkState.activeServer + endpoint.url()
    request = Request.Get(fullUrl)
    request.load(data, headers, params)
    httpResponse = request.send()
    return Response(httpResponse)

@_authenticated
def PATCH(endpoint: Endpoint, data, headers=dict(), **params) -> Response:
    _checkIsEndpoint(endpoint)
    fullUrl = _NetworkState.activeServer + endpoint.url()
    request = Request.Patch(fullUrl)
    request.load(data, headers, params)
    httpResponse = request.send()
    return Response(httpResponse)

@_authenticated
def POST(endpoint: Endpoint, data, headers=dict(), **params) -> Response:
    _checkIsEndpoint(endpoint)
    fullUrl = _NetworkState.activeServer + endpoint.url()
    request = Request.Post(fullUrl)
    request.load(data, headers, params)
    httpResponse = request.send()
    return Response(httpResponse)

@_authenticated
def PUT(endpoint: Endpoint, data, headers=dict(), **params) -> Response:
    _checkIsEndpoint(endpoint)
    fullUrl = _NetworkState.activeServer + endpoint.url()
    request = Request.Put(fullUrl)
    request.load(data, headers, params)
    httpResponse = request.send()
    return Response(httpResponse)

def _checkIsEndpoint(endpoint):
    if not issubclass(endpoint, Endpoint):
        raise ValueError("http methods must be given a pyblitz.Endpoint for argument `endpoint`")
