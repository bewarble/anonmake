from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from app.core.config import load_settings
from app.core.platform_security import encrypt_secret, hash_password, mask_secret
from app.database.session import SessionFactory
from app.models.bot_instance import BotInstance
from app.repositories.platform_admin import PlatformAdminRepository
from app.web.admin import login_redirect, page_context, require_session, templates

router = APIRouter(prefix="/admin/platform", include_in_schema=False)
settings = load_settings()


def require_superadmin(request: Request):
    principal = require_session(request)
    if principal is None:
        return None
    if not principal.is_superadmin:
        raise HTTPException(status_code=403, detail="SuperAdmin access required")
    return principal


@router.get("/admins", response_class=HTMLResponse)
async def admins_page(request: Request):
    if require_superadmin(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        repo = PlatformAdminRepository(session)
        admins = await repo.list_admins()
        bots = list(
            (await session.execute(select(BotInstance).order_by(BotInstance.id))).scalars()
        )
    return templates.TemplateResponse(
        request=request,
        name="platform_admins.html",
        context=page_context(
            request,
            title="Администраторы",
            section="platform_admins",
            admins=admins,
            bots=bots,
        ),
    )


@router.post("/admins")
async def create_admin(
    request: Request,
    email: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(...),
    role: str = Form("project_admin"),
    bot_ids: list[int] = Form(default=[]),
):
    if require_superadmin(request) is None:
        return login_redirect(request)
    if role not in {"superadmin", "project_admin"}:
        raise HTTPException(status_code=422, detail="Invalid role")
    if len(password) < 10:
        raise HTTPException(status_code=422, detail="Password is too short")

    async with SessionFactory() as session:
        repo = PlatformAdminRepository(session)
        if await repo.admin_by_email(email) is not None:
            raise HTTPException(status_code=409, detail="Admin already exists")
        await repo.create_admin(
            email=email,
            display_name=display_name,
            password_hash=hash_password(password),
            role=role,
            bot_ids=[] if role == "superadmin" else bot_ids,
        )
    return RedirectResponse("/admin/platform/admins", status_code=303)


@router.get("/payments", response_class=HTMLResponse)
async def payment_settings_page(request: Request):
    if require_superadmin(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        repo = PlatformAdminRepository(session)
        bots = list(
            (await session.execute(select(BotInstance).order_by(BotInstance.id))).scalars()
        )
        gateways = {
            bot.id: await repo.gateway_for_bot(bot.id)
            for bot in bots
        }
    return templates.TemplateResponse(
        request=request,
        name="platform_payments.html",
        context=page_context(
            request,
            title="Платёжные системы",
            section="platform_payments",
            bots=bots,
            gateways=gateways,
            mask_secret=mask_secret,
        ),
    )


@router.post("/payments/{bot_id}")
async def save_payment_settings(
    request: Request,
    bot_id: int,
    api_url: str = Form(...),
    api_token: str = Form(""),
    terminal_name: str = Form(...),
    binding_terminal_name: str = Form(...),
    recurrent_terminal_name: str = Form(...),
    payment_form_url_template: str = Form(...),
    webhook_secret: str = Form(""),
    is_active: bool = Form(False),
):
    if require_superadmin(request) is None:
        return login_redirect(request)

    async with SessionFactory() as session:
        repo = PlatformAdminRepository(session)
        current = await repo.gateway_for_bot(bot_id)
        values = {
            "api_url": api_url.strip(),
            "auth_header": "Authorization",
            "auth_prefix": "Bearer ",
            "protocol_version": "v2.0",
            "terminal_name": terminal_name.strip(),
            "binding_terminal_name": binding_terminal_name.strip(),
            "recurrent_terminal_name": recurrent_terminal_name.strip(),
            "payment_form_url_template": payment_form_url_template.strip(),
            "is_active": is_active,
            "api_token_encrypted": (
                encrypt_secret(api_token.strip(), settings.web_admin_secret)
                if api_token.strip()
                else (current.api_token_encrypted if current else "")
            ),
            "webhook_secret_encrypted": (
                encrypt_secret(webhook_secret.strip(), settings.web_admin_secret)
                if webhook_secret.strip()
                else (current.webhook_secret_encrypted if current else None)
            ),
        }
        await repo.upsert_gateway(
            bot_id=bot_id,
            provider="impaya",
            values=values,
        )
    return RedirectResponse("/admin/platform/payments", status_code=303)
