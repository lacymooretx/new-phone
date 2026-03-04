from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from new_phone.config import settings
from new_phone.events.publisher import EventPublisher
from new_phone.freeswitch.config_sync import ConfigSync
from new_phone.jobs.sms_retry import SMSRetryJob
from new_phone.middleware.error_handler import http_exception_handler, unhandled_exception_handler
from new_phone.middleware.metrics import MetricsMiddleware, metrics_endpoint
from new_phone.middleware.rate_limit import limiter
from new_phone.middleware.request_logging import RequestLoggingMiddleware
from new_phone.middleware.security_headers import SecurityHeadersMiddleware
from new_phone.services.camp_on_job import CampOnJob
from new_phone.services.email_service import EmailService
from new_phone.services.esl_event_listener import ESLEventListener
from new_phone.services.freeswitch_service import FreeSwitchService
from new_phone.services.storage_service import StorageService
from new_phone.services.tiering_job import TieringJob
from new_phone.ws.connection_manager import ConnectionManager

# Module-level references for health checks and config sync
redis_client: Redis | None = None
freeswitch_service: FreeSwitchService | None = None
config_sync: ConfigSync | None = None
storage_service: StorageService | None = None
esl_event_listener: ESLEventListener | None = None
email_service: EmailService | None = None
tiering_job: TieringJob | None = None
camp_on_job: CampOnJob | None = None
sms_retry_job: SMSRetryJob | None = None
event_publisher: EventPublisher | None = None
connection_manager: ConnectionManager | None = None


def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.dev.ConsoleRenderer()
            if settings.debug
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    global \
        redis_client, \
        freeswitch_service, \
        config_sync, \
        storage_service, \
        esl_event_listener, \
        email_service, \
        event_publisher, \
        connection_manager, \
        tiering_job, \
        camp_on_job, \
        sms_retry_job

    logger = structlog.get_logger()
    configure_logging()
    logger.info("starting_up", debug=settings.debug)

    # Redis
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis_client.ping()
        logger.info("redis_connected")
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))

    # FreeSWITCH ESL
    freeswitch_service = FreeSwitchService(
        host=settings.freeswitch_host,
        port=settings.freeswitch_esl_port,
        password=settings.freeswitch_esl_password,
    )
    await freeswitch_service.connect()

    # Config sync (wraps FS service for cache/profile management)
    config_sync = ConfigSync(freeswitch_service)

    # Sync gateway XML files from DB to shared volume on startup
    try:
        from new_phone.routers.sip_trunks import _startup_gateway_sync
        await _startup_gateway_sync()
        logger.info("gateway_sync_startup_complete")
    except Exception as e:
        logger.warning("gateway_sync_startup_failed", error=str(e))

    # MinIO storage
    storage_service = StorageService()
    try:
        await storage_service.init()
        logger.info("minio_connected")
    except Exception as e:
        logger.warning("minio_connection_failed", error=str(e))

    # Email service (voicemail-to-email)
    email_service = EmailService()

    # ESL event listener (persistent background subscription)
    esl_event_listener = ESLEventListener(storage=storage_service, email=email_service)
    await esl_event_listener.start()

    # Event publisher (Redis pub/sub)
    event_publisher = EventPublisher(redis_client)
    logger.info("event_publisher_initialized")

    # WebSocket connection manager (subscribes to Redis pub/sub)
    connection_manager = ConnectionManager(redis_client)
    await connection_manager.start_subscriber()

    # Recording storage tiering background job (daily)
    tiering_job = TieringJob(storage=storage_service)
    await tiering_job.start()

    # Camp-on expiry background job (every 60s)
    camp_on_job = CampOnJob(redis=redis_client)
    await camp_on_job.start()

    # SMS retry background job (every 30s)
    sms_retry_job = SMSRetryJob()
    await sms_retry_job.start()

    yield

    # Shutdown
    if sms_retry_job:
        await sms_retry_job.stop()
    if camp_on_job:
        await camp_on_job.stop()
    if tiering_job:
        await tiering_job.stop()
    if connection_manager:
        await connection_manager.stop_subscriber()
    if esl_event_listener:
        await esl_event_listener.stop()
    if redis_client:
        await redis_client.aclose()
    if freeswitch_service:
        await freeswitch_service.disconnect()
    logger.info("shutdown_complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Aspendora Connect API",
        description="Multi-tenant unified communications platform API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS — parse comma-separated origins from config
    if settings.cors_allowed_origins:
        cors_origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
    elif settings.debug:
        cors_origins = ["*"]
    else:
        cors_origins = []

    # Middleware (order matters — outermost first)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(MetricsMiddleware)

    # Prometheus metrics endpoint (optionally protected by bearer token)
    if settings.metrics_token:
        _expected_token = settings.metrics_token

        async def _protected_metrics(request: Request) -> Response:
            auth_header = request.headers.get("Authorization", "")
            if auth_header != f"Bearer {_expected_token}":
                return Response(status_code=403, content="Forbidden")
            return await metrics_endpoint(request)

        app.add_route("/metrics", _protected_metrics)
    else:
        app.add_route("/metrics", metrics_endpoint)

    # Error handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Routers
    from new_phone.freeswitch.xml_curl_router import router as xml_curl_router
    from new_phone.routers import (
        admin,
        ai_agents,
        analytics,
        audio_prompts,
        audit_logs,
        auth,
        boss_admin,
        building_webhooks,
        caller_id_rules,
        calls,
        camp_on,
        cdrs,
        compliance,
        compliance_monitoring,
        conference_bridges,
        connectwise,
        crm_config,
        devices,
        dids,
        disposition_codes,
        door_stations,
        extensions,
        follow_me,
        health,
        holiday_calendars,
        inbound_routes,
        ivr_menus,
        onboarding,
        outbound_routes,
        platform_telephony_providers,
        page_groups,
        paging_zones,
        panic_alerts,
        parking,
        phone_models,
        port_requests,
        queues,
        recording_tier,
        recordings,
        ring_groups,
        security_config,
        silent_intercom,
        sip_trunks,
        sites,
        sms_conversations,
        sms_provider_configs,
        sso_config,
        ten_dlc,
        tenant_telephony_providers,
        tenants,
        time_conditions,
        users,
        voicemail_boxes,
        voicemail_messages,
        webrtc,
        workforce_management,
    )

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(tenants.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(voicemail_boxes.router, prefix="/api/v1")
    app.include_router(extensions.router, prefix="/api/v1")
    app.include_router(calls.router, prefix="/api/v1")
    app.include_router(sip_trunks.router, prefix="/api/v1")
    app.include_router(dids.router, prefix="/api/v1")
    app.include_router(inbound_routes.router, prefix="/api/v1")
    app.include_router(outbound_routes.router, prefix="/api/v1")
    app.include_router(ring_groups.router, prefix="/api/v1")
    app.include_router(cdrs.router, prefix="/api/v1")
    app.include_router(recordings.router, prefix="/api/v1")
    app.include_router(recording_tier.router, prefix="/api/v1")
    app.include_router(camp_on.router, prefix="/api/v1")
    app.include_router(voicemail_messages.router, prefix="/api/v1")
    app.include_router(audio_prompts.router, prefix="/api/v1")
    app.include_router(time_conditions.router, prefix="/api/v1")
    app.include_router(ivr_menus.router, prefix="/api/v1")
    app.include_router(queues.router, prefix="/api/v1")
    app.include_router(parking.router, prefix="/api/v1")
    app.include_router(conference_bridges.router, prefix="/api/v1")
    app.include_router(page_groups.router, prefix="/api/v1")
    app.include_router(audit_logs.router, prefix="/api/v1")
    app.include_router(follow_me.router, prefix="/api/v1")
    app.include_router(caller_id_rules.router, prefix="/api/v1")
    app.include_router(holiday_calendars.router, prefix="/api/v1")
    app.include_router(phone_models.router, prefix="/api/v1")
    app.include_router(devices.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    app.include_router(webrtc.router, prefix="/api/v1")
    app.include_router(sms_conversations.router, prefix="/api/v1")
    app.include_router(sms_provider_configs.router, prefix="/api/v1")
    app.include_router(disposition_codes.router, prefix="/api/v1")
    app.include_router(sso_config.router, prefix="/api/v1")
    app.include_router(connectwise.router, prefix="/api/v1")
    app.include_router(crm_config.router, prefix="/api/v1")
    app.include_router(ai_agents.router, prefix="/api/v1")
    app.include_router(analytics.router, prefix="/api/v1")
    app.include_router(boss_admin.router, prefix="/api/v1")
    app.include_router(sites.router, prefix="/api/v1")
    app.include_router(compliance.router, prefix="/api/v1")
    app.include_router(compliance_monitoring.router, prefix="/api/v1")
    app.include_router(workforce_management.router, prefix="/api/v1")
    app.include_router(security_config.router, prefix="/api/v1")
    app.include_router(panic_alerts.router, prefix="/api/v1")
    app.include_router(silent_intercom.router, prefix="/api/v1")
    app.include_router(door_stations.router, prefix="/api/v1")
    app.include_router(paging_zones.router, prefix="/api/v1")
    app.include_router(building_webhooks.router, prefix="/api/v1")
    app.include_router(ten_dlc.router, prefix="/api/v1")
    app.include_router(port_requests.router, prefix="/api/v1")
    app.include_router(platform_telephony_providers.router, prefix="/api/v1")
    app.include_router(tenant_telephony_providers.router, prefix="/api/v1")
    app.include_router(onboarding.router, prefix="/api/v1")
    app.include_router(analytics.msp_router, prefix="/api/v1")

    # AI engine internal endpoints (no /api/v1 prefix — Docker network only)
    app.include_router(ai_agents.internal_router)

    # WebSocket events endpoint
    from new_phone.ws.router import router as ws_router

    app.include_router(ws_router, prefix="/api/v1")

    # FreeSWITCH xml_curl endpoints (no /api/v1 prefix — internal only)
    app.include_router(xml_curl_router)

    # Phone provisioning endpoint (no /api/v1 prefix — unauthenticated, called by phones)
    from new_phone.provisioning.router import router as provisioning_router

    app.include_router(provisioning_router)

    # Phone XML apps endpoint (no /api/v1 prefix — unauthenticated, MAC-based auth)
    from new_phone.phone_apps.router import router as phone_apps_router

    app.include_router(phone_apps_router)

    # SMS webhooks (no /api/v1 prefix — unauthenticated, called by SMS providers)
    from new_phone.sms.webhook_router import router as sms_webhook_router

    app.include_router(sms_webhook_router)

    # Building system webhooks (no /api/v1 prefix — unauthenticated, HMAC-validated)
    from new_phone.routers.building_webhook_inbound import router as building_webhook_inbound_router

    app.include_router(building_webhook_inbound_router)

    return app


app = create_app()
