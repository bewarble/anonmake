from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import delete, select

from app.core.config import load_settings
from app.core.platform_security import decrypt_secret, encrypt_secret
from app.database.session import SessionFactory
from app.models.bot_instance import BotInstance
from app.models.platform_admin import AdminProjectAccess, AdminUser, PaymentGatewayConfig
from app.models.project_setup import ProjectProfile, ProjectSetupDraft
from app.services.bot_credentials import fetch_bot_avatar, token_hint, verify_telegram_token
from app.web.admin import login_redirect, page_context, require_session, templates

router = APIRouter(prefix="/admin/projects/create", include_in_schema=False)
settings = load_settings()


def _superadmin(request: Request):
    principal = require_session(request)
    if principal is None:
        return None
    if not principal.is_superadmin:
        raise HTTPException(status_code=403, detail="Создание проекта доступно только суперадминистратору")
    return principal


async def _draft(session, draft_id: int) -> ProjectSetupDraft:
    item = await session.get(ProjectSetupDraft, draft_id)
    if item is None or item.status not in {"draft", "needs_attention", "ready"}:
        raise HTTPException(status_code=404, detail="Черновик проекта не найден")
    return item


def _wizard_context(request: Request, draft: ProjectSetupDraft, *, step: int, **extra):
    return page_context(
        request,
        title="Мастер создания проекта",
        section="projects",
        draft=draft,
        step=step,
        steps=("Основное", "Telegram", "Платежи", "Администратор", "Проверка"),
        **extra,
    )


@router.get("/wizard")
async def start_wizard(request: Request):
    principal = _superadmin(request)
    if principal is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        profile = await session.scalar(select(ProjectProfile).where(ProjectProfile.is_active.is_(True)).order_by(ProjectProfile.id))
        draft = ProjectSetupDraft(
            created_by_admin_id=principal.admin_id,
            profile_code=profile.code if profile else "anonymous_questions",
            current_step=1,
            status="draft",
            validation_errors=[],
        )
        session.add(draft)
        await session.commit()
        await session.refresh(draft)
    return RedirectResponse(f"/admin/projects/create/{draft.id}/basic", status_code=303)


@router.get("/{draft_id}/basic", response_class=HTMLResponse)
async def basic_page(request: Request, draft_id: int):
    if _superadmin(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        draft = await _draft(session, draft_id)
        profiles = list((await session.execute(select(ProjectProfile).where(ProjectProfile.is_active.is_(True)).order_by(ProjectProfile.id))).scalars())
    return templates.TemplateResponse(request=request, name="project_wizard.html", context=_wizard_context(request, draft, step=1, profiles=profiles))


@router.post("/{draft_id}/basic")
async def save_basic(request: Request, draft_id: int, profile_code: str = Form(...), display_name: str = Form(...), code: str = Form(...), description: str = Form("")):
    if _superadmin(request) is None:
        return login_redirect(request)
    normalized = code.strip().lower().replace("-", "_")
    if not normalized or not normalized.replace("_", "").isalnum() or len(normalized) > 32:
        return RedirectResponse(f"/admin/projects/create/{draft_id}/basic?error=code", status_code=303)
    async with SessionFactory() as session:
        draft = await _draft(session, draft_id)
        existing = await session.scalar(select(BotInstance.id).where(BotInstance.code == normalized))
        if existing:
            return RedirectResponse(f"/admin/projects/create/{draft_id}/basic?error=exists", status_code=303)
        draft.profile_code = profile_code
        draft.display_name = display_name.strip()[:96]
        draft.code = normalized
        draft.description = description.strip() or None
        draft.current_step = 2
        await session.commit()
    return RedirectResponse(f"/admin/projects/create/{draft_id}/telegram", status_code=303)


@router.get("/{draft_id}/telegram", response_class=HTMLResponse)
async def telegram_page(request: Request, draft_id: int):
    if _superadmin(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        draft = await _draft(session, draft_id)
    return templates.TemplateResponse(request=request, name="project_wizard.html", context=_wizard_context(request, draft, step=2, error=request.query_params.get("error")))


@router.get("/{draft_id}/telegram/avatar")
async def telegram_avatar(request: Request, draft_id: int):
    if _superadmin(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        draft = await _draft(session, draft_id)
        if not draft.telegram_token_encrypted or not draft.telegram_bot_id:
            raise HTTPException(status_code=404, detail="Аватар Telegram-бота не найден")
        token = decrypt_secret(
            draft.telegram_token_encrypted,
            settings.web_admin_secret,
        )
    avatar = await fetch_bot_avatar(token, draft.telegram_bot_id)
    if avatar is None:
        raise HTTPException(status_code=404, detail="У Telegram-бота нет аватара")
    payload, media_type = avatar
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.post("/{draft_id}/telegram")
async def save_telegram(request: Request, draft_id: int, telegram_token: str = Form(...)):
    if _superadmin(request) is None:
        return login_redirect(request)
    token = telegram_token.strip()
    try:
        me = await verify_telegram_token(token)
    except Exception:
        return RedirectResponse(f"/admin/projects/create/{draft_id}/telegram?error=token", status_code=303)
    async with SessionFactory() as session:
        draft = await _draft(session, draft_id)
        duplicate = await session.scalar(select(BotInstance.id).where(BotInstance.username == me.username))
        if duplicate:
            return RedirectResponse(f"/admin/projects/create/{draft_id}/telegram?error=exists", status_code=303)
        draft.telegram_username = me.username
        draft.telegram_bot_id = me.id
        draft.telegram_token_encrypted = encrypt_secret(token, settings.web_admin_secret)
        draft.telegram_token_hint = token_hint(token)
        draft.telegram_verified_at = datetime.now(timezone.utc)
        draft.current_step = 3
        await session.commit()
    return RedirectResponse(f"/admin/projects/create/{draft_id}/payments", status_code=303)


@router.get("/{draft_id}/payments", response_class=HTMLResponse)
async def payments_page(request: Request, draft_id: int):
    if _superadmin(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        draft = await _draft(session, draft_id)
    return templates.TemplateResponse(request=request, name="project_wizard.html", context=_wizard_context(request, draft, step=3))


@router.post("/{draft_id}/payments")
async def save_payments(request: Request, draft_id: int, api_url: str = Form(""), api_token: str = Form(""), terminal_name: str = Form(""), binding_terminal_name: str = Form(""), recurrent_terminal_name: str = Form(""), payment_form_url_template: str = Form(""), webhook_secret: str = Form("")):
    if _superadmin(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        draft = await _draft(session, draft_id)
        draft.impaya_api_url = api_url.strip() or None
        draft.impaya_api_token_encrypted = encrypt_secret(api_token.strip(), settings.web_admin_secret) if api_token.strip() else None
        draft.impaya_terminal_name = terminal_name.strip() or None
        draft.impaya_binding_terminal_name = binding_terminal_name.strip() or None
        draft.impaya_recurrent_terminal_name = recurrent_terminal_name.strip() or None
        draft.impaya_payment_form_url_template = payment_form_url_template.strip() or None
        draft.impaya_webhook_secret_encrypted = encrypt_secret(webhook_secret.strip(), settings.web_admin_secret) if webhook_secret.strip() else None
        draft.current_step = 4
        await session.commit()
    return RedirectResponse(f"/admin/projects/create/{draft_id}/administrator", status_code=303)


@router.get("/{draft_id}/administrator", response_class=HTMLResponse)
async def administrator_page(request: Request, draft_id: int):
    if _superadmin(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        draft = await _draft(session, draft_id)
        admins = list((await session.execute(select(AdminUser).where(AdminUser.is_active.is_(True)).order_by(AdminUser.display_name))).scalars())
    return templates.TemplateResponse(request=request, name="project_wizard.html", context=_wizard_context(request, draft, step=4, admins=admins))


@router.post("/{draft_id}/administrator")
async def save_administrator(request: Request, draft_id: int, assigned_admin_id: int | None = Form(None)):
    if _superadmin(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        draft = await _draft(session, draft_id)
        draft.assigned_admin_id = assigned_admin_id or None
        draft.current_step = 5
        await session.commit()
    return RedirectResponse(f"/admin/projects/create/{draft_id}/review", status_code=303)


def _readiness(draft: ProjectSetupDraft) -> list[str]:
    errors: list[str] = []
    if not draft.display_name or not draft.code:
        errors.append("Не заполнены основные сведения")
    if not draft.telegram_token_encrypted or not draft.telegram_username or not draft.telegram_verified_at:
        errors.append("Telegram-токен не проверен")
    impaya_values = (draft.impaya_api_url, draft.impaya_api_token_encrypted, draft.impaya_terminal_name, draft.impaya_binding_terminal_name, draft.impaya_recurrent_terminal_name, draft.impaya_payment_form_url_template)
    if any(impaya_values) and not all(impaya_values):
        errors.append("Настройки Impaya заполнены не полностью")
    return errors


@router.get("/{draft_id}/review", response_class=HTMLResponse)
async def review_page(request: Request, draft_id: int):
    if _superadmin(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        draft = await _draft(session, draft_id)
        errors = _readiness(draft)
        draft.validation_errors = errors
        draft.status = "ready" if not errors else "needs_attention"
        await session.commit()
        assigned_admin = await session.get(AdminUser, draft.assigned_admin_id) if draft.assigned_admin_id else None
    return templates.TemplateResponse(request=request, name="project_wizard.html", context=_wizard_context(request, draft, step=5, readiness_errors=errors, assigned_admin=assigned_admin))


@router.post("/{draft_id}/launch")
async def launch_project(request: Request, draft_id: int):
    if _superadmin(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        draft = await _draft(session, draft_id)
        errors = _readiness(draft)
        if errors:
            draft.validation_errors = errors
            draft.status = "needs_attention"
            await session.commit()
            return RedirectResponse(f"/admin/projects/create/{draft_id}/review", status_code=303)
        duplicate = await session.scalar(select(BotInstance.id).where((BotInstance.code == draft.code) | (BotInstance.username == draft.telegram_username)))
        if duplicate:
            draft.validation_errors = ["Проект с таким кодом или Telegram-именем уже существует"]
            draft.status = "needs_attention"
            await session.commit()
            return RedirectResponse(f"/admin/projects/create/{draft_id}/review", status_code=303)

        bot = BotInstance(
            code=draft.code,
            username=draft.telegram_username,
            display_name=draft.display_name,
            description=draft.description,
            profile_code=draft.profile_code,
            setup_status="running",
            runtime_mode="managed",
            telegram_bot_id=draft.telegram_bot_id,
            token_encrypted=draft.telegram_token_encrypted,
            token_hint=draft.telegram_token_hint,
            token_verified_at=draft.telegram_verified_at,
            is_active=True,
            is_maintenance=False,
        )
        session.add(bot)
        await session.flush()

        if draft.impaya_api_url:
            session.add(PaymentGatewayConfig(
                bot_id=bot.id,
                provider="impaya",
                api_url=draft.impaya_api_url,
                api_token_encrypted=draft.impaya_api_token_encrypted or "",
                auth_header="Authorization",
                auth_prefix="Bearer ",
                protocol_version="v2.0",
                terminal_name=draft.impaya_terminal_name or "",
                binding_terminal_name=draft.impaya_binding_terminal_name or "",
                recurrent_terminal_name=draft.impaya_recurrent_terminal_name or "",
                payment_form_url_template=draft.impaya_payment_form_url_template or "",
                webhook_secret_encrypted=draft.impaya_webhook_secret_encrypted,
                is_active=True,
            ))
        if draft.assigned_admin_id:
            session.add(AdminProjectAccess(admin_user_id=draft.assigned_admin_id, bot_id=bot.id))

        draft.status = "launched"
        draft.launched_bot_id = bot.id
        draft.validation_errors = []
        await session.commit()
    return RedirectResponse(f"/admin/projects/{bot.code}?notice=created", status_code=303)


@router.post("/{draft_id}/delete")
async def delete_draft(request: Request, draft_id: int):
    if _superadmin(request) is None:
        return login_redirect(request)
    async with SessionFactory() as session:
        draft = await _draft(session, draft_id)
        await session.delete(draft)
        await session.commit()
    return RedirectResponse("/admin/projects?notice=draft_deleted", status_code=303)
