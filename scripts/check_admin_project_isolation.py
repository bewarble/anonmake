from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def function_source(path: str, name: str) -> str:
    source = (ROOT / path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=path)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.unparse(node)
    raise AssertionError(f"Function not found: {path}:{name}")


def main() -> None:
    routes = "app/web/admin_stage29.py"
    repo = "app/web/admin_repository_stage29.py"

    # Source detail/edit/delete must use a bot-scoped lookup, never a naked PK get.
    helper = function_source(routes, "_scoped_source")
    assert "TrafficSource.id == source_id" in helper
    assert "TrafficSource.bot_id == bot_id" in helper
    for name in ("source_details", "source_edit", "source_delete"):
        body = function_source(routes, name)
        assert "_scoped_source" in body, name
        assert "session.get(TrafficSource" not in body, name

    # Mutating actions are project-only and establish the matching CurrentBot.
    assert "_selected_bot(request)" in function_source(routes, "source_new_submit")
    assert "_bot_context(selected_bot)" in function_source(routes, "source_new_submit")
    assert "_selected_bot(request)" in function_source(routes, "broadcast_create")
    assert "_bot_context(selected_bot)" in function_source(routes, "broadcast_create")

    # Referral links use the source owner's bot username, not the global primary bot.
    details = function_source(routes, "source_details")
    assert "session.get(BotInstance, source.bot_id)" in details
    assert "source_referral_url(source, owner.username)" in details

    # API chart must preserve the selected project scope.
    chart = function_source(routes, "chart_api")
    assert "bot_id=_scope_bot_id(request)" in chart.replace(" ", "")

    stage29 = (ROOT / repo).read_text(encoding="utf-8")
    # Block/dead-user metrics and previous-period payment comparisons must scope bot_id.
    assert "failure_filters.append(DeliveryOutbox.bot_id == self.bot_id)" in stage29
    assert "dead_filters.append(DeliveryOutbox.bot_id == self.bot_id)" in stage29
    assert "User.bot_id == self.bot_id" in function_source(repo, "_dead_users")
    assert "filters.append(PaymentAttempt.bot_id == self.bot_id)" in function_source(
        repo, "_payment_count_comparison"
    )

    print("Admin project isolation check: OK")
    print("Source read/edit/delete IDOR: blocked")
    print("Source/broadcast mutations: selected-project context enforced")
    print("Chart, blocked users and payment deltas: project-scoped")
    print("Referral URLs: owning bot username")


if __name__ == "__main__":
    main()
