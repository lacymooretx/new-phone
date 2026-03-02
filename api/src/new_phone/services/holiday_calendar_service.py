import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from new_phone.db.rls import set_tenant_context
from new_phone.models.holiday_calendar import HolidayCalendar, HolidayEntry
from new_phone.schemas.holiday_calendar import HolidayCalendarCreate, HolidayCalendarUpdate


class HolidayCalendarService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_calendars(self, tenant_id: uuid.UUID) -> list[HolidayCalendar]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(HolidayCalendar)
            .where(HolidayCalendar.tenant_id == tenant_id, HolidayCalendar.is_active.is_(True))
            .options(selectinload(HolidayCalendar.entries))
            .order_by(HolidayCalendar.name)
        )
        return list(result.scalars().all())

    async def get_calendar(
        self, tenant_id: uuid.UUID, calendar_id: uuid.UUID
    ) -> HolidayCalendar | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(HolidayCalendar)
            .where(
                HolidayCalendar.id == calendar_id,
                HolidayCalendar.tenant_id == tenant_id,
            )
            .options(selectinload(HolidayCalendar.entries))
        )
        return result.scalar_one_or_none()

    async def create_calendar(
        self, tenant_id: uuid.UUID, data: HolidayCalendarCreate
    ) -> HolidayCalendar:
        await set_tenant_context(self.db, tenant_id)

        existing = await self.db.execute(
            select(HolidayCalendar).where(
                HolidayCalendar.tenant_id == tenant_id,
                HolidayCalendar.name == data.name,
                HolidayCalendar.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Holiday calendar '{data.name}' already exists")

        calendar = HolidayCalendar(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
        )
        # Add entries
        for entry_data in data.entries:
            entry = HolidayEntry(
                name=entry_data.name,
                date=entry_data.date,
                recur_annually=entry_data.recur_annually,
                all_day=entry_data.all_day,
                start_time=entry_data.start_time,
                end_time=entry_data.end_time,
            )
            calendar.entries.append(entry)

        self.db.add(calendar)
        await self.db.commit()
        await self.db.refresh(calendar)
        return calendar

    async def update_calendar(
        self, tenant_id: uuid.UUID, calendar_id: uuid.UUID, data: HolidayCalendarUpdate
    ) -> HolidayCalendar:
        calendar = await self.get_calendar(tenant_id, calendar_id)
        if not calendar:
            raise ValueError("Holiday calendar not found")

        update_data = data.model_dump(exclude_unset=True)

        if "name" in update_data and update_data["name"] is not None:
            calendar.name = update_data["name"]
        if "description" in update_data:
            calendar.description = update_data["description"]

        # Replace-all entries if provided
        if "entries" in update_data and update_data["entries"] is not None:
            # Clear existing entries
            calendar.entries.clear()
            await self.db.flush()
            # Add new entries
            for entry_data in data.entries:
                entry = HolidayEntry(
                    calendar_id=calendar.id,
                    name=entry_data.name,
                    date=entry_data.date,
                    recur_annually=entry_data.recur_annually,
                    all_day=entry_data.all_day,
                    start_time=entry_data.start_time,
                    end_time=entry_data.end_time,
                )
                calendar.entries.append(entry)

        await self.db.commit()
        await self.db.refresh(calendar)
        return calendar

    async def deactivate(
        self, tenant_id: uuid.UUID, calendar_id: uuid.UUID
    ) -> HolidayCalendar:
        calendar = await self.get_calendar(tenant_id, calendar_id)
        if not calendar:
            raise ValueError("Holiday calendar not found")
        calendar.is_active = False
        await self.db.commit()
        await self.db.refresh(calendar)
        return calendar
