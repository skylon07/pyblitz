_fromAuthorizedMethodKey = object()

class Request:
    def __init__(self, *args, **kwargs):
        if len(args) != 1 or args[0] is not _fromAuthorizedMethodKey:
            raise RuntimeError("Cannot initialize Request() directly;\
                use a @classmethod constructor instead for the http call you want to make")
        self.__authorized_init__(*args, **kwargs)

    def __authorized_init__(self, fromAuthorizedMethodKey, serverUrl: str):
        assert fromAuthorizedMethodKey is _fromAuthorizedMethodKey, "Invalid call made to create Request()"

        pass # TODO

    @classmethod
    def Delete(self, serverUrl: str):
        pass # TODO

    @classmethod
    def Get(self, serverUrl: str):
        pass # TODO

    @classmethod
    def Patch(self, serverUrl: str):
        pass # TODO

    @classmethod
    def Post(self, serverUrl: str):
        pass # TODO

    @classmethod
    def Put(self, serverUrl: str):
        pass # TODO

    def load(self, data, headers: dict, params: dict):
        pass # TODO

    def send(self):
        pass