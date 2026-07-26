from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class ImpayaResult:
    success: bool
    data: dict[str, Any]

    @property
    def error_code(self) -> str | None:
        return self.data.get("error_code")

    @property
    def error_message(self) -> str | None:
        return self.data.get("error_message") or self.data.get("message")


class ImpayaClient:
    """Minimal asynchronous Impaya API client.

    Authentication header is configurable because terminal credentials can be
    issued in different formats. By default the token is sent in Authorization.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        terminal_name: str,
        *,
        auth_header: str = "Authorization",
        auth_prefix: str = "",
        timeout: float = 20.0,
    ) -> None:
        self.terminal_name = terminal_name
        value = f"{auth_prefix}{token}" if auth_prefix else token
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={auth_header: value, "Content-Type": "application/json"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def bind_init(
        self,
        *,
        customer_operation_id: str,
        merchant_user_id: str,
        success_url: str,
        fail_url: str,
    ) -> ImpayaResult:
        payload = {
            "action": "verify_and_bind",
            "customer_operation_id": customer_operation_id,
            "merchant_user_id": merchant_user_id,
            "payment_option_action": "bind_recurrent",
            "preferred_payment_option": {
                "card": {"terminal_name": self.terminal_name}
            },
            "redirect_data": {
                "success_redirect_url": success_url,
                "fail_redirect_url": fail_url,
            },
            "description": "Подключение подписки",
        }
        return await self._post("/payment-option/bind-init", payload)

    async def recurrent_pay(
        self,
        *,
        customer_operation_id: str,
        amount: int,
        binding_id: str,
        impaya_user_id: str,
        merchant_user_id: str,
    ) -> ImpayaResult:
        payload = {
            "customer_operation_id": customer_operation_id,
            "amount": amount,
            "terminal_name": self.terminal_name,
            "is_recurrent": True,
            "payment_initiator": "MIT",
            "merchant_user_id": merchant_user_id,
            "payment_option_data": {
                "impaya_pay": {
                    "binding_id": binding_id,
                    "user_id": impaya_user_id,
                    "merchant_user_id": merchant_user_id,
                }
            },
            "description": "Продление подписки",
        }
        return await self._post("/order/pay", payload)

    async def state(
        self, *, customer_operation_id: str
    ) -> ImpayaResult:
        response = await self._client.get(
            "/order/state/extended",
            params={
                "terminal_name": self.terminal_name,
                "customer_operation_id": customer_operation_id,
            },
        )
        response.raise_for_status()
        data = response.json()
        return ImpayaResult(bool(data.get("success")), data)

    async def _post(self, path: str, payload: dict[str, Any]) -> ImpayaResult:
        response = await self._client.post(path, json=payload)
        response.raise_for_status()
        data = response.json()
        return ImpayaResult(bool(data.get("success")), data)
