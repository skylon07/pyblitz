from threading import Timer

from .requests import Request

class RequestThrottler:
    def __init__(self):
        self._throttle = 0
        self._requestQueue = []
        self._pendingTimer = None

    def setThrottle(self, requestRateSecs: int):
        assert type(requestRateSecs) is int
        self._throttle = requestRateSecs

    def sendRequest(self, request: Request):
        self._requestQueue.append(request)
        self._attemptSendNextRequest()

    @property
    def _requestIsPending(self):
        return self._pendingTimer is not None

    def _attemptSendNextRequest(self):
        if len(self._requestQueue) == 0 or self._requestIsPending:
            return
        assert self._pendingTimer is None

        if self._throttle > 0:
            self._pendingTimer = Timer(self._throttle, self._onTimerEnd)
            self._pendingTimer.start()
        nextRequest = self._requestQueue.pop(0)
        nextRequest.send()

    def _onTimerEnd(self):
        self._pendingTimer = None
        self._attemptSendNextRequest()
    