"""Tests for FreeSWITCH config sync service."""

from unittest.mock import AsyncMock

import pytest

from new_phone.freeswitch.config_sync import ConfigSync


@pytest.fixture
def mock_fs():
    fs = AsyncMock()
    fs.flush_xml_cache = AsyncMock(return_value=True)
    fs.sofia_profile_rescan = AsyncMock(return_value=True)
    fs.kill_gateway = AsyncMock(return_value=True)
    fs.reload_xml = AsyncMock(return_value=True)
    return fs


@pytest.fixture
def sync(mock_fs):
    return ConfigSync(mock_fs)


class TestConfigSync:

    async def test_notify_directory_change(self, sync, mock_fs):
        await sync.notify_directory_change()
        mock_fs.flush_xml_cache.assert_called_once()

    async def test_notify_dialplan_change(self, sync, mock_fs):
        await sync.notify_dialplan_change()
        mock_fs.flush_xml_cache.assert_called_once()

    async def test_notify_gateway_change_with_name(self, sync, mock_fs):
        await sync.notify_gateway_change("acme-test-trunk")
        mock_fs.kill_gateway.assert_called_once_with("acme-test-trunk")
        mock_fs.flush_xml_cache.assert_called_once()
        mock_fs.sofia_profile_rescan.assert_called_once()

    async def test_notify_gateway_change_without_name(self, sync, mock_fs):
        await sync.notify_gateway_change()
        mock_fs.kill_gateway.assert_not_called()
        mock_fs.flush_xml_cache.assert_called_once()
        mock_fs.sofia_profile_rescan.assert_called_once()

    async def test_notify_gateway_create(self, sync, mock_fs):
        await sync.notify_gateway_create()
        mock_fs.flush_xml_cache.assert_called_once()
        mock_fs.sofia_profile_rescan.assert_called_once()
