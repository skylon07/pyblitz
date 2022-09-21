import json
from typing import Callable, Union

from ..common import Schema


_fromAuthorizedMethodKey = object()

class Request:
    def __init__(self, *args, **kwargs):
        if len(args) == 0 or args[0] is not _fromAuthorizedMethodKey:
            raise RuntimeError("Cannot initialize Request() directly;\
                use a @classmethod constructor instead for the http call you want to make")
        self.__authorized_init__(*args, **kwargs)

    def __authorized_init__(self, fromAuthorizedMethodKey, toUrl: str, httpMethodFn: Callable):
        assert fromAuthorizedMethodKey is _fromAuthorizedMethodKey, "Invalid call made to create Request()"
        self._url = toUrl
        self._methodFn = httpMethodFn
        self._loaded = False

    @classmethod
    def Delete(cls, toUrl: str):
        self = cls(_fromAuthorizedMethodKey, toUrl, cls._getSession().delete)
        return self

    @classmethod
    def Get(cls, toUrl: str):
        self = cls(_fromAuthorizedMethodKey, toUrl, cls._getSession().get)
        return self

    @classmethod
    def Patch(cls, toUrl: str):
        self = cls(_fromAuthorizedMethodKey, toUrl, cls._getSession().patch)
        return self

    @classmethod
    def Post(cls, toUrl: str):
        self = cls(_fromAuthorizedMethodKey, toUrl, cls._getSession().post)
        return self

    @classmethod
    def Put(cls, toUrl: str):
        self = cls(_fromAuthorizedMethodKey, toUrl, cls._getSession().put)
        return self

    @classmethod
    def _getSession(self):
        from .network import _NetworkState
        return _NetworkState.session

    def load(self, data: Union[str, dict, Schema], headers: dict, params: dict):
        """Loads data, headers, and query parameters into this Request

        `data` can be many things, but ultimately it must be converted down to a string
        to pass into the inner http request. Currently this function supports `data` of types
        `str`, `dict`, or `Schema`.
        """
        
        self._headers = headers
        self._params = params
        
        data = self._manipulateDataToStr(data)
        assert type(data) is str
        self._dataStr = data
        self._loaded = True

    def _manipulateDataToStr(self, data):
        """There is one goal: convert `data` into a meaningful http request string (recursively!)"""
        if data is None:
            data = ""
        else:
            data = json.dumps(data, default=self._serializeFn)
        return data

    def _serializeFn(self, obj):
        if isinstance(obj, Schema):
            return obj.serialize()
        else:
            assert "this" is "not handled", "Unconsidered serialize case"

    def send(self):
        assert self._loaded, "Cannot send request before calling load()"
        return self._methodFn(self._url, data=self._dataStr, headers=self._headers, params=self._params)
