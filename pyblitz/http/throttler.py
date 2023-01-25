from threading import Timer
from typing import Union
from time import sleep

from .requests import Request


class RequestThrottler:
    def __init__(self):
        self._throttle = 0
        self._pendingTimer = None

    def setThrottle(self, requestRateSecs: Union[float, int]):
        assert type(requestRateSecs) in (float, int)
        self._throttle = requestRateSecs

    def sendRequest(self, request: Request):
        self._waitUntilOutOfTimeout()
        self._startTimeout()
        return request.send()

    @property
    def _inTimeout(self):
        return self._pendingTimer is not None

    def _waitUntilOutOfTimeout(self):
        sleepTime = self._throttle / 100
        sleepsDone = 0
        while self._inTimeout:
            sleep(sleepTime)
            sleepsDone += 1
            if sleepsDone == 50:
                sleepTime *= 10
            elif sleepsDone == 105:
                sleepTime *= 5

    def _startTimeout(self):
        if self._throttle > 0:
            self._pendingTimer = Timer(self._throttle, self._onTimerEnd)
            self._pendingTimer.start()

    def _onTimerEnd(self):
        self._clearTimer()

    def _clearTimer(self):
        self._pendingTimer = None
