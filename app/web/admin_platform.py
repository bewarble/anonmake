from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from app.core.config import load_settings
from app.core.platform_security import encrypt_secret, hash_password
from app.database.session import SessionFactory
from app.models.bot_instance import BotInstance
from app.repositories.platform_admin import PlatformAdminRepository
from app.web.admin import login_redirect, page_context, require_session, templates

router = APIRouter(prefix="/admin/platform", include_in_schema=False)
settings = load_settings()
VALID_ROLES = {"superadmin", "project_admin"}


def require_superadmin(request: Request):
    principal = require_session(request)
    if principal is None:
        return None
    if not principal.is_superadmin:
        raise HTTPException(
            status_code=403,
            detail="Раздел доступен только суперадминистратору",
        )
    return principal


def redirect_with_notice(path: str, notice: str) -> RedirectResponse:
    return RedirectResponse(
        f"{path}?{urlencode({'notice': notice})}",
        status_code=303,
    )


async def _bots(session):
    return list(
        (
            await session.execute(
                select(BotInstance).order_by(BotInstance.id)
            )
        ).scalars()
    )


def _validate_account(role: str, password: str | None = None) -> None:
    if role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail="Некорректная роль")
    if password is not None and password and len(password) < 10:
        raise HTTPException(
            status_code=422,
            detail="Пароль должен содержать не менее 10 символов",
        )


@router.get("/admins", response_class=HTMLResponse)
async def admins_page(request: Request):
    if require_superadmin(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        repo = PlatformAdminRepository(session)
        admins = await repo.list_admins()
        bots = await _bots(session)
        access = {
            admin.id: await repo.access_bot_ids(admin.id)
            for admin in admins
        }
    return templates.TemplateResponse(
        request=request,
        name="platform_admins.html",
        context=page_context(
            request,
            title="Администраторы",
            section="platform_admins",
            admins=admins,
            bots=bots,
            access=access,
            notice=request.query_params.get("notice"),
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
    _validate_account(role, password)
    async with SessionFactory() as session:
        repo = PlatformAdminRepository(session)
        if await repo.admin_by_email_any(email) is not None:
            raise HTTPException(
                status_code=409,
                detail="Аккаунт с такой электронной почтой уже существует",
            )
        await repo.create_admin(
            email=email,
            display_name=display_name,
            password_hash=hash_password(password),
            role=role,
            bot_ids=[] if role == "superadmin" else bot_ids,
        )
    return redirect_with_notice("/admin/platform/admins", "created")


@router.get("/admins/{admin_id}/edit", response_class=HTMLResponse)
async def edit_admin_page(request: Request, admin_id: int):
    principal = require_superadmin(request)
    if principal is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        repo = PlatformAdminRepository(session)
        admin = await repo.admin_by_id(admin_id)
        if admin is None:
            raise HTTPException(status_code=404, detail="Аккаунт не найден")
        bots = await _bots(session)
        access_bot_ids = await repo.access_bot_ids(admin.id)
    return templates.TemplateResponse(
        request=request,
        name="platform_admin_edit.html",
        context=page_context(
            request,
            title="Редактирование аккаунта",
            section="platform_admins",
            admin=admin,
            bots=bots,
            access_bot_ids=access_bot_ids,
            is_current_account=principal.admin_id == admin.id,
        ),
    )


@router.post("/admins/{admin_id}/edit")
async def update_admin_account(
    request: Request,
    admin_id: int,
    email: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(""),
    role: str = Form("project_admin"),
    is_active: bool = Form(False),
    bot_ids: list[int] = Form(default=[]),
):
    principal = require_superadmin(request)
    if principal is None:
        return login_redirect(request)
    _validate_account(role, password)

    async with SessionFactory() as session:
        repo = PlatformAdminRepository(session)
        admin = await repo.admin_by_id(admin_id)
        if admin is None:
            raise HTTPException(status_code=404, detail="Аккаунт не найден")

        duplicate = await repo.admin_by_email_any(email)
        if duplicate is not None and duplicate.id != admin.id:
            raise HTTPException(
                status_code=409,
                detail="Электронная почта уже используется другим аккаунтом",
            )

        removes_active_superadmin = (
            admin.is_superadmin
            and admin.is_active
            and (role != "superadmin" or not is_active)
        )
        if removes_active_superadmin and await repo.active_superadmin_count() <= 1:
            raise HTTPException(
                status_code=409,
                detail="Нельзя отключить или понизить последнего активного суперадминистратора",
            )
        if principal.admin_id == admin.id and not is_active:
            raise HTTPException(
                status_code=409,
                detail="Нельзя отключить собственный аккаунт",
            )

        await repo.update_admin(
            admin,
            email=email,
            display_name=display_name,
            role=role,
            is_active=is_active,
            bot_ids=bot_ids,
            password_hash=hash_password(password) if password else None,
        )
    return redirect_with_notice("/admin/platform/admins", "updated")


@router.post("/admins/{admin_id}/delete")
async def delete_admin_account(request: Request, admin_id: int):
    principal = require_superadmin(request)
    if principal is None:
        return login_redirect(request)
    if principal.admin_id == admin_id:
        raise HTTPException(
            status_code=409,
            detail="Нельзя удалить собственный аккаунт",
        )

    async with SessionFactory() as session:
        repo = PlatformAdminRepository(session)
        admin = await repo.admin_by_id(admin_id)
        if admin is None:
            raise HTTPException(status_code=404, detail="Аккаунт не найден")
        if (
            admin.is_superadmin
            and admin.is_active
            and await repo.active_superadmin_count() <= 1
        ):
            raise HTTPException(
                status_code=409,
                detail="Нельзя удалить последнего активного суперадминистратора",
            )
        await repo.delete_admin(admin)
    return redirect_with_notice("/admin/platform/admins", "deleted")


@router.get("/payments", response_class=HTMLResponse)
async def payment_settings_page(request: Request):
    if require_superadmin(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        repo = PlatformAdminRepository(session)
        bots = await _bots(session)
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
            notice=request.query_params.get("notice"),
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
        bot = await session.scalar(
            select(BotInstance).where(BotInstance.id == bot_id)
        )
        if bot is None:
            raise HTTPException(status_code=404, detail="Проект не найден")
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
    return redirect_with_notice("/admin/platform/payments", "saved")
