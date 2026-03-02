import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.models.phone_model import PhoneModel
from new_phone.schemas.phone_model import PhoneModelCreate, PhoneModelUpdate


class PhoneModelService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_phone_models(self, active_only: bool = True) -> list[PhoneModel]:
        stmt = select(PhoneModel).order_by(PhoneModel.manufacturer, PhoneModel.model_name)
        if active_only:
            stmt = stmt.where(PhoneModel.is_active.is_(True))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_phone_model(self, model_id: uuid.UUID) -> PhoneModel | None:
        result = await self.db.execute(
            select(PhoneModel).where(PhoneModel.id == model_id)
        )
        return result.scalar_one_or_none()

    async def create_phone_model(self, data: PhoneModelCreate) -> PhoneModel:
        model = PhoneModel(**data.model_dump())
        self.db.add(model)
        await self.db.commit()
        await self.db.refresh(model)
        return model

    async def update_phone_model(
        self, model_id: uuid.UUID, data: PhoneModelUpdate
    ) -> PhoneModel:
        model = await self.get_phone_model(model_id)
        if not model:
            raise ValueError("Phone model not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(model, key, value)

        await self.db.commit()
        await self.db.refresh(model)
        return model

    async def delete_phone_model(self, model_id: uuid.UUID) -> PhoneModel:
        model = await self.get_phone_model(model_id)
        if not model:
            raise ValueError("Phone model not found")

        model.is_active = False
        await self.db.commit()
        await self.db.refresh(model)
        return model
