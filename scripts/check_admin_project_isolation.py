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
    assert "failure_filters.append(DeliveryOutbox.bot_id == self.bot_id)" in stage29
    assert "dead_filters.append(DeliveryOutbox.bot_id == self.bot_id)" in stage29
    assert "User.bot_id == self.bot_id" in function_source(repo, "_dead_users")
    assert "filters.append(PaymentAttempt.bot_id == self.bot_id)" in function_source(
        repo, "_payment_count_comparison"
    )

    # Legacy Stage27 CRM routes remain registered, so they must also pass bot_id.
    stage27_routes = "app/web/admin_stage27.py"
    for name in (
        "dashboard_v2",
        "crm_users",
        "crm_user_details",
        "crm_source_details",
        "broadcasts",
    ):
        assert "_scope_bot_id(request)" in function_source(stage27_routes, name), name
    crm_repo = "app/web/admin_repository_stage27.py"
    crm_text = (ROOT / crm_repo).read_text(encoding="utf-8")
    assert "self.bot_id = bot_id" in crm_text
    assert "TrafficSource.bot_id == self.bot_id" in function_source(crm_repo, "source_details")
    assert "Broadcast.bot_id == self.bot_id" in function_source(crm_repo, "broadcasts")
    assert "User.bot_id == self.bot_id" in function_source(crm_repo, "users")

    # Stage28.1 overview/source-create are active legacy routes too.
    stage28_routes = "app/web/admin_stage28_1.py"
    overview = function_source(stage28_routes, "overview")
    assert "ScopedWebAdminRepository(session, bot_id=bot_id)" in overview
    assert "WebAdminProRepository(session, bot_id=bot_id)" in overview
    source_create = function_source(stage28_routes, "source_create_submit")
    assert "_selected_bot(request)" in source_create
    assert "_bot_context(selected_bot)" in source_create

    pro_repo = "app/web/admin_repository_stage28.py"
    assert "self.bot_id = bot_id" in (ROOT / pro_repo).read_text(encoding="utf-8")
    assert "PaymentAttempt.bot_id == self.bot_id" in function_source(pro_repo, "periods")

    scoped_repo = "app/web/admin_scoped_repository.py"
    scoped_dashboard = function_source(scoped_repo, "dashboard")
    for needle in (
        "User.bot_id == self.bot_id",
        "DeliveryOutbox.bot_id == self.bot_id",
        "Subscription.bot_id == self.bot_id",
        "PaymentMethod.bot_id == self.bot_id",
        "PaymentAttempt.bot_id == self.bot_id",
        "TrafficSource.bot_id == self.bot_id",
    ):
        assert needle in scoped_dashboard, needle

    # Global search means cross-entity search, not cross-project access.
    search_route = function_source("app/web/admin_complete.py", "global_search")
    for model in ("User", "PaymentAttempt", "PaymentMethod", "TrafficSource"):
        assert f"_scope_filter(request, {model})" in search_route, model

    print("Admin project isolation check: OK")
    print("Stage29 source IDOR and metrics: isolated")
    print("Stage27 CRM/users/sources/broadcasts: isolated")
    print("Stage28 overview/source creation: isolated")
    print("Scoped legacy dashboard: isolated")
    print("Admin cross-entity search: selected-project scoped")


if __name__ == "__main__":
    main()
