"""Tests for new_phone.services.analytics_service — CDR analytics queries."""

import uuid
from unittest.mock import MagicMock

from new_phone.services.analytics_service import AnalyticsService
from tests.unit.conftest import TENANT_ACME_ID


class TestGetCallSummary:
    async def test_returns_summary(self, mock_db):
        row = MagicMock()
        row.total_calls = 100
        row.inbound = 60
        row.outbound = 30
        row.internal = 10
        row.answered = 80
        row.no_answer = 10
        row.busy = 5
        row.failed = 2
        row.voicemail = 2
        row.cancelled = 1
        row.avg_duration_seconds = 120.5
        row.total_duration_seconds = 12050

        result_mock = MagicMock()
        result_mock.one.return_value = row
        mock_db.execute.return_value = result_mock

        service = AnalyticsService(mock_db)
        result = await service.get_call_summary(TENANT_ACME_ID)
        assert result["total_calls"] == 100
        assert result["inbound"] == 60
        assert result["avg_duration_seconds"] == 120.5

    async def test_empty_data_returns_zeros(self, mock_db):
        row = MagicMock()
        row.total_calls = 0
        row.inbound = 0
        row.outbound = 0
        row.internal = 0
        row.answered = 0
        row.no_answer = 0
        row.busy = 0
        row.failed = 0
        row.voicemail = 0
        row.cancelled = 0
        row.avg_duration_seconds = 0
        row.total_duration_seconds = 0

        result_mock = MagicMock()
        result_mock.one.return_value = row
        mock_db.execute.return_value = result_mock

        service = AnalyticsService(mock_db)
        result = await service.get_call_summary(TENANT_ACME_ID)
        assert result["total_calls"] == 0


class TestGetCallVolumeTrend:
    async def test_returns_trend_data(self, mock_db):
        row1 = MagicMock()
        row1.period = "2024-01-01"
        row1.total = 10
        row1.inbound = 6
        row1.outbound = 3
        row1.internal = 1

        result_mock = MagicMock()
        result_mock.all.return_value = [row1]
        mock_db.execute.return_value = result_mock

        service = AnalyticsService(mock_db)
        result = await service.get_call_volume_trend(TENANT_ACME_ID)
        assert result["granularity"] == "daily"
        assert len(result["data"]) == 1
        assert result["data"][0]["total"] == 10

    async def test_empty_returns_empty_data(self, mock_db):
        result_mock = MagicMock()
        result_mock.all.return_value = []
        mock_db.execute.return_value = result_mock

        service = AnalyticsService(mock_db)
        result = await service.get_call_volume_trend(TENANT_ACME_ID)
        assert result["data"] == []


class TestGetExtensionActivity:
    async def test_returns_activity_list(self, mock_db):
        row = MagicMock()
        row.extension_id = uuid.uuid4()
        row.extension_number = "100"
        row.extension_name = "John Smith"
        row.total_calls = 50
        row.inbound = 30
        row.outbound = 20
        row.missed = 5
        row.avg_duration_seconds = 90.0
        row.total_duration_seconds = 4500

        result_mock = MagicMock()
        result_mock.all.return_value = [row]
        mock_db.execute.return_value = result_mock

        service = AnalyticsService(mock_db)
        result = await service.get_extension_activity(TENANT_ACME_ID)
        assert len(result) == 1
        assert result[0]["extension_number"] == "100"
        assert result[0]["total_calls"] == 50


class TestGetDurationDistribution:
    async def test_returns_buckets(self, mock_db):
        row = MagicMock()
        row.under_30s = 10
        row.s30_to_1m = 20
        row.m1_to_5m = 30
        row.m5_to_15m = 20
        row.m15_to_30m = 10
        row.over_30m = 5
        row.total = 95

        result_mock = MagicMock()
        result_mock.one.return_value = row
        mock_db.execute.return_value = result_mock

        service = AnalyticsService(mock_db)
        result = await service.get_duration_distribution(TENANT_ACME_ID)
        assert len(result) == 6
        assert result[0]["bucket"] == "< 30s"
        assert result[0]["count"] == 10


class TestGetMSPOverview:
    async def test_returns_overview(self, mock_db):
        # Multiple sequential execute calls
        tenant_count = MagicMock()
        tenant_count.scalar.return_value = 5

        today_count = MagicMock()
        today_count.scalar.return_value = 100

        week_count = MagicMock()
        week_count.scalar.return_value = 500

        ext_count = MagicMock()
        ext_count.scalar.return_value = 50

        tenant_rows = MagicMock()
        tenant_rows.all.return_value = []

        today_per = MagicMock()
        today_per.all.return_value = []

        total_per = MagicMock()
        total_per.all.return_value = []

        ext_per = MagicMock()
        ext_per.all.return_value = []

        mock_db.execute.side_effect = [
            tenant_count,
            today_count,
            week_count,
            ext_count,
            tenant_rows,
            today_per,
            total_per,
            ext_per,
        ]

        service = AnalyticsService(mock_db)
        result = await service.get_msp_overview()
        assert result["total_tenants"] == 5
        assert result["total_calls_today"] == 100
        assert result["system_health"] == "healthy"
