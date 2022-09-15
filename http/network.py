import requests
import json


class _NetworkState:
    isAuthed = False
    activeServer = None
    servers = dict()
    session = requests.Session()


def registerServer(name, url):
    _NetworkState.servers[name] = url

def getServer(name):
    return _NetworkState.servers[name]

def getServerNames():
    return list(_NetworkState.servers.keys())

def setActiveServer(name):
    if name not in _NetworkState.servers:
        raise ValueError("Server '{}' is not registered!".format(name))
    _NetworkState.activeServer = _NetworkState.servers[name]


def setAuth(token):
    _NetworkState.session.headers.update({
        "authorization": "Bearer {}".format(token),
    })
    _NetworkState.isAuthed = True


def _authenticated(fn):
    def authedFn(*args, **kwargs):
        if _NetworkState.activeServer is None:
            raise RuntimeError("Cannot make network requests until a server is chosen via pyblitz.http.setActiveServer()")
        if not _NetworkState.isAuthed:
            raise RuntimeError("Cannot make network requests until authentication is set with pyblitz.http.setAuth()")
        return fn(*args, **kwargs)
    return authedFn


@_authenticated
def DELETE(endpoint, headers=dict(), data=None, **params):
    from ..api import Endpoint, Schema
    assert issubclass(endpoint, Endpoint)
    
    if isinstance(data, Schema):
        data = json.dumps(data.serialize())
    return _NetworkState.session.delete(_NetworkState.activeServer + endpoint.url(), data=data, headers=headers, params=params)

@_authenticated
def GET(endpoint, headers=dict(), data=None, **params):
    from ..api import Endpoint, Schema
    assert issubclass(endpoint, Endpoint)
    
    if isinstance(data, Schema):
        data = json.dumps(data.serialize())
    return _NetworkState.session.get(_NetworkState.activeServer + endpoint.url(), data=data, headers=headers, params=params)

@_authenticated
def PATCH(endpoint, data, headers=dict(), **params):
    from ..api import Endpoint, Schema
    assert issubclass(endpoint, Endpoint)
    
    if isinstance(data, Schema):
        data = json.dumps(data.serialize())
    return _NetworkState.session.patch(_NetworkState.activeServer + endpoint.url(), data=data, headers=headers, params=params)

@_authenticated
def POST(endpoint, data, headers=dict(), **params):
    from ..api import Endpoint, Schema
    assert issubclass(endpoint, Endpoint)
    
    if isinstance(data, Schema):
        data = json.dumps(data.serialize())
    return _NetworkState.session.post(_NetworkState.activeServer + endpoint.url(), data=data, headers=headers, params=params)

@_authenticated
def PUT(endpoint, data, headers=dict(), **params):
    from ..api import Endpoint, Schema
    assert issubclass(endpoint, Endpoint)
    
    if isinstance(data, Schema):
        data = json.dumps(data.serialize())
    return _NetworkState.session.put(_NetworkState.activeServer + endpoint.url(), headers=headers, params=params)
