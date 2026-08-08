from __future__ import annotations

from fastapi.responses import HTMLResponse

from app.database.session import SessionFactory
from app.repositories.reveals import RevealRepository
from app.services.payment_notifications import finalize_checkout_and_notify

SUCCESS_PATH = "/payments/return/success/{checkout_token}"


async def process_checkout(checkout_token: str) -> str:
    async with SessionFactory() as session:
        checkout = await RevealRepository(session).get_by_token(
            checkout_token,
            for_update=True,
        )
        if checkout is None:
            return "not_found"

        return await finalize_checkout_and_notify(
            session,
            None,  # type: ignore[arg-type]
            None,  # type: ignore[arg-type]
            checkout,
            payment_form_url_template="",
        )


async def payment_success(checkout_token: str) -> HTMLResponse:
    result = await process_checkout(checkout_token)

    if result in {"notified", "already_notified"}:
        body = (
            "<h1>✅ Всё готово!</h1>"
            "<p>Вернитесь в Telegram — VIP статус уже активирован.</p>"
            "<p>VIP активирован. Результат отправлен в Telegram.</p>"
        )
    elif result == "pending":
        body = (
            "<h1>Платёж обрабатывается</h1>"
            "<p>Бот автоматически пришлёт результат после подтверждения.</p>"
        )
    else:
        body = (
            "<h1>Не удалось завершить обработку</h1>"
            "<p>Вернитесь в Telegram. Система продолжит сверку платежа.</p>"
        )

    return HTMLResponse(
        "<!doctype html><html lang='ru'><meta charset='utf-8'>"
        f"<title>AnonMake</title><body>{body}</body></html>"
    )


def install_payment_return(app) -> None:
    if getattr(app.state, "project_payment_return_installed", False):
        return

    app.router.routes[:] = [
        route
        for route in app.router.routes
        if not (
            getattr(route, "path", None) == SUCCESS_PATH
            and "GET" in (getattr(route, "methods", None) or set())
        )
    ]
    app.add_api_route(
        SUCCESS_PATH,
        payment_success,
        methods=["GET"],
        response_class=HTMLResponse,
        include_in_schema=True,
    )
    app.state.project_payment_return_installed = True
