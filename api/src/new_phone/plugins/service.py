import uuid

import httpx
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.plugins.models import (
    Plugin,
    PluginEventLog,
    PluginStatus,
    TenantPlugin,
)

logger = structlog.get_logger()

WEBHOOK_TIMEOUT = 10.0


class PluginService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Catalog ──────────────────────────────────────────────────────

    async def list_available_plugins(self) -> list[Plugin]:
        result = await self.db.execute(
            select(Plugin)
            .where(Plugin.is_published.is_(True))
            .order_by(Plugin.name)
        )
        return list(result.scalars().all())

    async def get_plugin(self, plugin_id: uuid.UUID) -> Plugin | None:
        result = await self.db.execute(
            select(Plugin).where(Plugin.id == plugin_id)
        )
        return result.scalar_one_or_none()

    # ── Install / Uninstall ──────────────────────────────────────────

    async def install_plugin(
        self,
        tenant_id: uuid.UUID,
        plugin_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> TenantPlugin:
        await set_tenant_context(self.db, tenant_id)

        # Check not already installed
        existing = await self.db.execute(
            select(TenantPlugin).where(
                TenantPlugin.tenant_id == tenant_id,
                TenantPlugin.plugin_id == plugin_id,
            )
        )
        if existing.scalar_one_or_none():
            msg = "Plugin already installed for this tenant"
            raise ValueError(msg)

        tp = TenantPlugin(
            tenant_id=tenant_id,
            plugin_id=plugin_id,
            status=PluginStatus.INSTALLED,
            installed_by_user_id=user_id,
        )
        self.db.add(tp)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(tp)
        return tp

    async def uninstall_plugin(
        self, tenant_id: uuid.UUID, plugin_id: uuid.UUID
    ) -> bool:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(TenantPlugin).where(
                TenantPlugin.tenant_id == tenant_id,
                TenantPlugin.plugin_id == plugin_id,
            )
        )
        tp = result.scalar_one_or_none()
        if not tp:
            return False
        await self.db.delete(tp)
        await self.db.commit()
        return True

    # ── Activate / Deactivate ────────────────────────────────────────

    async def activate_plugin(
        self, tenant_id: uuid.UUID, plugin_id: uuid.UUID
    ) -> TenantPlugin | None:
        tp = await self._get_tenant_plugin(tenant_id, plugin_id)
        if not tp:
            return None
        tp.status = PluginStatus.ACTIVE
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(tp)
        return tp

    async def deactivate_plugin(
        self, tenant_id: uuid.UUID, plugin_id: uuid.UUID
    ) -> TenantPlugin | None:
        tp = await self._get_tenant_plugin(tenant_id, plugin_id)
        if not tp:
            return None
        tp.status = PluginStatus.INACTIVE
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(tp)
        return tp

    # ── Config ───────────────────────────────────────────────────────

    async def update_plugin_config(
        self, tenant_id: uuid.UUID, plugin_id: uuid.UUID, config: dict
    ) -> TenantPlugin | None:
        tp = await self._get_tenant_plugin(tenant_id, plugin_id)
        if not tp:
            return None
        tp.config = config
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(tp)
        return tp

    # ── Installed List ───────────────────────────────────────────────

    async def list_installed_plugins(
        self, tenant_id: uuid.UUID
    ) -> list[TenantPlugin]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(TenantPlugin)
            .where(TenantPlugin.tenant_id == tenant_id)
            .order_by(TenantPlugin.installed_at.desc())
        )
        return list(result.scalars().all())

    # ── Hook Dispatch ────────────────────────────────────────────────

    async def dispatch_hook(
        self, tenant_id: uuid.UUID, hook_type: str, payload: dict
    ) -> list[PluginEventLog]:
        """Send hook events to all active plugins that subscribe to the given hook_type."""
        await set_tenant_context(self.db, tenant_id)

        result = await self.db.execute(
            select(TenantPlugin)
            .where(
                TenantPlugin.tenant_id == tenant_id,
                TenantPlugin.status == PluginStatus.ACTIVE,
            )
        )
        tenant_plugins = list(result.scalars().all())

        logs: list[PluginEventLog] = []
        for tp in tenant_plugins:
            plugin = tp.plugin
            if not plugin or hook_type not in (plugin.hook_types or []):
                continue
            if not plugin.webhook_url:
                continue

            log = PluginEventLog(
                tenant_id=tenant_id,
                plugin_id=plugin.id,
                hook_type=hook_type,
                payload=payload,
            )

            try:
                async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
                    resp = await client.post(
                        plugin.webhook_url,
                        json={
                            "hook_type": hook_type,
                            "tenant_id": str(tenant_id),
                            "plugin_id": str(plugin.id),
                            "payload": payload,
                        },
                        headers={"Content-Type": "application/json"},
                    )
                    log.response_status = resp.status_code
                    if resp.status_code >= 400:
                        log.error_message = f"HTTP {resp.status_code}"
            except Exception as exc:
                log.error_message = str(exc)[:1024]
                logger.warning(
                    "plugin_hook_dispatch_failed",
                    plugin_id=str(plugin.id),
                    hook_type=hook_type,
                    error=str(exc),
                )

            self.db.add(log)
            logs.append(log)

        if logs:
            await self.db.flush()
            await self.db.commit()

        return logs

    # ── Event Logs ───────────────────────────────────────────────────

    async def list_event_logs(
        self,
        tenant_id: uuid.UUID,
        plugin_id: uuid.UUID,
        page: int = 1,
        per_page: int = 50,
    ) -> tuple[list[PluginEventLog], int]:
        await set_tenant_context(self.db, tenant_id)

        filters = [
            PluginEventLog.tenant_id == tenant_id,
            PluginEventLog.plugin_id == plugin_id,
        ]

        total_result = await self.db.execute(
            select(func.count(PluginEventLog.id)).where(*filters)
        )
        total = total_result.scalar() or 0

        offset = (page - 1) * per_page
        result = await self.db.execute(
            select(PluginEventLog)
            .where(*filters)
            .order_by(PluginEventLog.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        return list(result.scalars().all()), total

    # ── Helpers ──────────────────────────────────────────────────────

    async def _get_tenant_plugin(
        self, tenant_id: uuid.UUID, plugin_id: uuid.UUID
    ) -> TenantPlugin | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(TenantPlugin).where(
                TenantPlugin.tenant_id == tenant_id,
                TenantPlugin.plugin_id == plugin_id,
            )
        )
        return result.scalar_one_or_none()
