"""Tests for new_phone.services.phone_model_service — phone model CRUD."""

import uuid
from unittest.mock import MagicMock

import pytest

from new_phone.services.phone_model_service import PhoneModelService
from tests.unit.conftest import make_scalar_result, make_scalars_result


def _make_phone_model(**overrides):
    model = MagicMock()
    model.id = overrides.get("id", uuid.uuid4())
    model.manufacturer = overrides.get("manufacturer", "Yealink")
    model.model_name = overrides.get("model_name", "T54W")
    model.model_family = overrides.get("model_family", "T5x")
    model.is_active = overrides.get("is_active", True)
    return model


class TestListPhoneModels:
    async def test_returns_list(self, mock_db):
        m1 = _make_phone_model(model_name="T54W")
        m2 = _make_phone_model(model_name="T46U")
        mock_db.execute.return_value = make_scalars_result([m1, m2])

        service = PhoneModelService(mock_db)
        result = await service.list_phone_models()
        assert len(result) == 2

    async def test_empty(self, mock_db):
        mock_db.execute.return_value = make_scalars_result([])
        service = PhoneModelService(mock_db)
        result = await service.list_phone_models()
        assert result == []


class TestGetPhoneModel:
    async def test_found(self, mock_db):
        model = _make_phone_model(model_name="T54W")
        mock_db.execute.return_value = make_scalar_result(model)
        service = PhoneModelService(mock_db)
        result = await service.get_phone_model(model.id)
        assert result.model_name == "T54W"

    async def test_not_found(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = PhoneModelService(mock_db)
        result = await service.get_phone_model(uuid.uuid4())
        assert result is None


class TestCreatePhoneModel:
    async def test_success(self, mock_db):
        from new_phone.schemas.phone_model import PhoneModelCreate

        service = PhoneModelService(mock_db)
        data = PhoneModelCreate(
            manufacturer="Yealink",
            model_name="T54W",
            model_family="T5x",
            max_line_keys=16,
        )
        await service.create_phone_model(data)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()


class TestUpdatePhoneModel:
    async def test_success(self, mock_db):
        from new_phone.schemas.phone_model import PhoneModelUpdate

        model = _make_phone_model()
        mock_db.execute.return_value = make_scalar_result(model)
        service = PhoneModelService(mock_db)
        data = PhoneModelUpdate(model_name="T54W-Pro")
        await service.update_phone_model(model.id, data)
        mock_db.commit.assert_awaited()

    async def test_not_found_raises(self, mock_db):
        from new_phone.schemas.phone_model import PhoneModelUpdate

        mock_db.execute.return_value = make_scalar_result(None)
        service = PhoneModelService(mock_db)
        data = PhoneModelUpdate(model_name="x")
        with pytest.raises(ValueError, match="not found"):
            await service.update_phone_model(uuid.uuid4(), data)


class TestDeletePhoneModel:
    async def test_success(self, mock_db):
        model = _make_phone_model(is_active=True)
        mock_db.execute.return_value = make_scalar_result(model)
        service = PhoneModelService(mock_db)
        await service.delete_phone_model(model.id)
        assert model.is_active is False

    async def test_not_found_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = PhoneModelService(mock_db)
        with pytest.raises(ValueError, match="not found"):
            await service.delete_phone_model(uuid.uuid4())
