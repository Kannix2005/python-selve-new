"""
Command methods must survive a missing gateway reply (#50) and gateway log
events must not flood the HA log (#48).
"""
import logging
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock

import pytest

from selve import Selve
from selve.util import LogEventResponse
from selve.util.protocol import DriveCommandIveo, LogType


def _make_selve():
    return Selve(port=None, discover=False, develop=False, logger=Mock())


class TestExecutedWithoutReply:
    """executeCommandSyncWithResponse returns False on timeout / gateway fault."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("call", [
        lambda s: s.iveoTeach(0),
        lambda s: s.iveoLearn(0),
        lambda s: s.iveoCommandManual(0, DriveCommandIveo.UP),
        lambda s: s.iveoFactoryReset(0),
    ])
    async def test_false_reply_returns_false_instead_of_crashing(self, call):
        s = _make_selve()
        s.executeCommandSyncWithResponse = AsyncMock(return_value=False)
        assert await call(s) is False

    @pytest.mark.asyncio
    async def test_real_reply_still_passes_executed_through(self):
        s = _make_selve()
        s.executeCommandSyncWithResponse = AsyncMock(
            return_value=SimpleNamespace(executed=True)
        )
        assert await s.iveoTeach(0) is True

    def test_helper(self):
        assert Selve._executed(False) is False
        assert Selve._executed(None) is False
        assert Selve._executed(True) is False  # a bare bool is no confirmation
        assert Selve._executed(SimpleNamespace(executed=True)) is True
        assert Selve._executed(SimpleNamespace(executed=False)) is False


def _log_event(description, log_type):
    resp = LogEventResponse.__new__(LogEventResponse)
    resp.logCode, resp.logStamp, resp.logValue = "1301", "A35324934", "2"
    resp.logDescription = description
    resp.logType = log_type
    return resp


class TestGatewayLogLevels:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("log_type", list(LogType))
    async def test_command_overwritten_is_debug(self, log_type):
        s = _make_selve()
        await s.processEventResponse(_log_event("COMMEO: Command overwritten (02)!", log_type))
        assert s._LOGGER.log.call_args[0][0] == logging.DEBUG

    @pytest.mark.asyncio
    @pytest.mark.parametrize("log_type,level", [
        (LogType.INFO, logging.DEBUG),
        (LogType.WARNING, logging.INFO),
        (LogType.ERROR, logging.WARNING),
    ])
    async def test_other_events_one_level_lower(self, log_type, level):
        s = _make_selve()
        await s.processEventResponse(_log_event("Something else", log_type))
        assert s._LOGGER.log.call_args[0][0] == level
