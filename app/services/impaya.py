from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class ImpayaResult:
    success: bool
    data: dict[str, Any]
    status_code: int | None = None

    @property
    def error_code(self) -> str | None:
        value = self.data.get("error_code")
        return str(value) if value is not None else None

    @property
    def error_message(self) -> str | None:
        value = (
            self.data.get("error_message")
            or self.data.get("message")
            or self.data.get("detail")
        )
        return str(value) if value is not None else None


def normalize_auth_prefix(value: str) -> str:
    cleaned = value.strip().strip('"“”\'‘’')
    if cleaned and not cleaned.endswith(" "):
        cleaned += " "
    return cleaned


class ImpayaClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        terminal_name: str,
        *,
        auth_header: str = "Authorization",
        auth_prefix: str = "Bearer ",
        protocol_version: str = "v2.0",
        recurrent_terminal_name: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.terminal_name = terminal_name
        self.recurrent_terminal_name = (
            recurrent_terminal_name or terminal_name
        )
        prefix = normalize_auth_prefix(auth_prefix)
        authorization = f"{prefix}{token.strip()}" if prefix else token.strip()

        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers={
                auth_header: authorization,
                "Content-Type": "application/json",
                "protocol": protocol_version,
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def create_trial_invoice(
        self,
        *,
        customer_operation_id: str,
        amount: int,
        merchant_user_id: str,
        success_url: str,
        fail_url: str,
    ) -> ImpayaResult:
        payload = {
            "action": "authorize",
            "amount": amount,
            "customer_operation_id": customer_operation_id,
            "merchant_user_id": merchant_user_id,
            "customization_form": {
                "button_label": "Оплатить 1 ₽",
            },
            "goods": [
                {
                    "name": "Привязка карты",
                    "price": amount,
                    "tax": 6,
                    "payment_subject_type": 4,
                    "payment_method_type": 4,
                    "agent_type": 0,
                    "supplier": {
                        "name": "",
                        "inn": "",
                        "phone_numbers": None,
                    },
                    "quantity": 1,
                }
            ],
            "lifetime": 602703,
            "payment_option_action": "bind_recurrent",
            "post_action": "void",
            "preferred_payment_option": {
                "card": {
                    "routing": "hard",
                    "terminal_name": self.terminal_name,
                }
            },
            "redirect_data": {
                "success_redirect_url": success_url,
                "fail_redirect_url": fail_url,
            },
        }

        return await self._post("/invoice", payload)

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
            "terminal_name": self.recurrent_terminal_name,
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
            "description": "Продление подписки AnonMake",
        }
        return await self._request("POST", "/order/pay", json=payload)

    async def state(
        self,
        *,
        customer_operation_id: str,
        recurrent: bool = False,
    ) -> ImpayaResult:
        terminal_name = (
            self.recurrent_terminal_name if recurrent else self.terminal_name
        )
        return await self._request(
            "GET",
            "/order/state/extended",
            params={
                "terminal_name": terminal_name,
                "customer_operation_id": customer_operation_id,
            },
        )

    async def _post(
        self,
        path: str,
        payload: dict,
    ) -> ImpayaResult:
        return await self._request(
            "POST",
            path,
            json=payload,
        )

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> ImpayaResult:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            return ImpayaResult(
                False,
                {
                    "error_code": "HTTP_CLIENT_ERROR",
                    "error_message": str(exc),
                },
            )

        try:
            data = response.json()
        except ValueError:
            data = {
                "error_code": f"HTTP_{response.status_code}",
                "error_message": response.text[:1000],
            }

        if not isinstance(data, dict):
            data = {"response": data}

        if not response.is_success and "error_code" not in data:
            data["error_code"] = f"HTTP_{response.status_code}"

        return ImpayaResult(
            response.is_success and bool(data.get("success")),
            data,
            response.status_code,
        )
