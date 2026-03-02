import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from new_phone.db.rls import set_tenant_context
from new_phone.models.ivr_menu import IVRMenu, IVRMenuOption
from new_phone.schemas.ivr_menu import IVRMenuCreate, IVRMenuUpdate


class IVRMenuService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_menus(self, tenant_id: uuid.UUID) -> list[IVRMenu]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(IVRMenu)
            .where(IVRMenu.tenant_id == tenant_id, IVRMenu.is_active.is_(True))
            .options(selectinload(IVRMenu.options))
            .order_by(IVRMenu.name)
        )
        return list(result.scalars().all())

    async def get_menu(
        self, tenant_id: uuid.UUID, menu_id: uuid.UUID
    ) -> IVRMenu | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(IVRMenu)
            .where(IVRMenu.id == menu_id, IVRMenu.tenant_id == tenant_id)
            .options(selectinload(IVRMenu.options))
        )
        return result.scalar_one_or_none()

    async def create_menu(
        self, tenant_id: uuid.UUID, data: IVRMenuCreate
    ) -> IVRMenu:
        await set_tenant_context(self.db, tenant_id)

        # Check for duplicate name
        existing = await self.db.execute(
            select(IVRMenu).where(
                IVRMenu.tenant_id == tenant_id,
                IVRMenu.name == data.name,
                IVRMenu.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"IVR menu '{data.name}' already exists")

        menu = IVRMenu(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            greet_long_prompt_id=data.greet_long_prompt_id,
            greet_short_prompt_id=data.greet_short_prompt_id,
            invalid_sound_prompt_id=data.invalid_sound_prompt_id,
            exit_sound_prompt_id=data.exit_sound_prompt_id,
            timeout=data.timeout,
            max_failures=data.max_failures,
            max_timeouts=data.max_timeouts,
            inter_digit_timeout=data.inter_digit_timeout,
            digit_len=data.digit_len,
            exit_destination_type=data.exit_destination_type,
            exit_destination_id=data.exit_destination_id,
            enabled=data.enabled,
        )
        self.db.add(menu)
        await self.db.flush()

        # Create options
        for opt_data in data.options:
            opt = IVRMenuOption(
                ivr_menu_id=menu.id,
                digits=opt_data.digits,
                action_type=opt_data.action_type,
                action_target_id=opt_data.action_target_id,
                action_target_value=opt_data.action_target_value,
                label=opt_data.label,
                position=opt_data.position,
            )
            self.db.add(opt)

        await self.db.commit()
        await self.db.refresh(menu)
        return menu

    async def update_menu(
        self, tenant_id: uuid.UUID, menu_id: uuid.UUID, data: IVRMenuUpdate
    ) -> IVRMenu:
        menu = await self.get_menu(tenant_id, menu_id)
        if not menu:
            raise ValueError("IVR menu not found")

        update_data = data.model_dump(exclude_unset=True)
        options_data = update_data.pop("options", None)

        for key, value in update_data.items():
            setattr(menu, key, value)

        # Replace-all pattern for options
        if options_data is not None:
            # Delete existing options
            for opt in list(menu.options):
                await self.db.delete(opt)
            await self.db.flush()

            # Create new options
            for opt_data in data.options:
                opt = IVRMenuOption(
                    ivr_menu_id=menu.id,
                    digits=opt_data.digits,
                    action_type=opt_data.action_type,
                    action_target_id=opt_data.action_target_id,
                    action_target_value=opt_data.action_target_value,
                    label=opt_data.label,
                    position=opt_data.position,
                )
                self.db.add(opt)

        await self.db.commit()
        await self.db.refresh(menu)
        return menu

    async def deactivate(
        self, tenant_id: uuid.UUID, menu_id: uuid.UUID
    ) -> IVRMenu:
        menu = await self.get_menu(tenant_id, menu_id)
        if not menu:
            raise ValueError("IVR menu not found")
        menu.is_active = False
        await self.db.commit()
        await self.db.refresh(menu)
        return menu
