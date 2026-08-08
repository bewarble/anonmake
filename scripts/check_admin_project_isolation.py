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

    helper = function_source(routes, "_scoped_source")
    assert "TrafficSource.id == source_id" in helper
    assert "TrafficSource.bot_id == bot_id" in helper
    for name in ("source_details", "source_edit", "source_delete"):
        body = function_source(routes, name)
        assert "_scoped_source" in body, name
        assert "session.get(TrafficSource" not in body, name

    assert "_selected_bot(request)" in function_source(routes, "source_new_submit")
    assert "_bot_context(selected_bot)" in function_source(routes, "source_new_submit")
    assert "_selected_bot(request)" in function_source(routes, "broadcast_create")
    assert "_bot_context(selected_bot)" in function_source(routes, "broadcast_create")

    details = function_source(routes, "source_details")
    assert "session.get(BotInstance, source.bot_id)" in details
    assert "source_referral_url(source, owner.username)" in details

    chart = function_source(routes, "chart_api")
    assert "bot_id=_scope_bot_id(request)" in chart.replace(" ", "")

    stage29 = (ROOT / repo).read_text(encoding="utf-8")
    assert "failure_filters.append(DeliveryOutbox.bot_id == self.bot_id)" in stage29
    assert "dead_filters.append(DeliveryOutbox.bot_id == self.bot_id)" in stage29
    assert "User.bot_id == self.bot_id" in function_source(repo, "_dead_users")
    assert "filters.append(PaymentAttempt.bot_id == self.bot_id)" in function_source(
        repo, "_payment_count_comparison"
    )

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

    stage28 = "app/web/admin_stage28.py"
    pro_dashboard = function_source(stage28, "pro_dashboard")
    assert "_scope_bot_id(request)" in pro_dashboard
    assert "ScopedWebAdminRepository(session, bot_id=bot_id)" in pro_dashboard
    assert "WebCrmRepository(session, bot_id=bot_id)" in pro_dashboard
    assert "WebAdminProRepository(session, bot_id=bot_id)" in pro_dashboard
    assert "bot_id=_scope_bot_id(request)" in function_source(
        stage28, "analytics_periods"
    ).replace(" ", "")

    stage28_1 = "app/web/admin_stage28_1.py"
    overview = function_source(stage28_1, "overview")
    assert "ScopedWebAdminRepository(session, bot_id=bot_id)" in overview
    assert "WebAdminProRepository(session, bot_id=bot_id)" in overview
    source_create = function_source(stage28_1, "source_create_submit")
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

    search_route = function_source("app/web/admin_complete.py", "global_search")
    for model in ("User", "PaymentAttempt", "PaymentMethod", "TrafficSource"):
        assert f"_scope_filter(request, {model})" in search_route, model

    stage31 = "app/web/admin_stage31.py"
    entities = function_source(stage31, "load_entities")
    assert "User.bot_id == bot_id" in entities
    assert "Subscription.bot_id == user.bot_id" in entities
    assert "PaymentMethod.bot_id == user.bot_id" in entities
    assert "session.get(User" not in entities
    control = function_source(stage31, "user_control_submit")
    assert "bot_id=selected_bot_id(request)" in control.replace(" ", "")
    assert "load_impaya_config(session, settings, owner_bot.id)" in control
    assert "create_impaya_client(config)" in control
    assert "with bot_context(owner_bot)" in control
    subscriptions = function_source(stage31, "subscriptions")
    assert "Subscription.bot_id == bot_id" in subscriptions
    assert "User.bot_id == bot_id" in subscriptions

    support = "app/services/admin_subscription_control.py"
    assert "require_current_bot().id" in function_source(support, "_require_current_subscription")
    assert "lock_subscription_transaction" in function_source(support, "set_auto_renew")
    assert "cancel_auto_renew" in function_source(support, "set_auto_renew")
    assert "lock_subscription_transaction" in function_source(support, "extend_access")

    crm_core = "app/repositories/crm.py"
    require_user = function_source(crm_core, "_require_user")
    assert "User.id == user_id" in require_user
    assert "User.bot_id == bot_id" in require_user
    for name in ("profile", "add_note", "assign_tag", "remove_tag", "record_event"):
        assert "_require_user" in function_source(crm_core, name), name
    assert "TrafficSource.bot_id == user.bot_id" in function_source(crm_core, "profile")

    cleanup = "app/repositories/marketing_cleanup.py"
    source_lookup = function_source(cleanup, "source")
    assert "require_current_bot().id" in source_lookup
    assert "TrafficSource.id == source_id" in source_lookup
    assert "TrafficSource.bot_id == bot_id" in source_lookup
    assert "session.get(TrafficSource" not in source_lookup
    delete_source = function_source(cleanup, "delete_source")
    assert "self.source(source_id)" in delete_source
    assert "session.get(TrafficSource" not in delete_source

    print("Admin project isolation check: OK")
    print("Stage29 source IDOR and metrics: isolated")
    print("Stage27 CRM/users/sources/broadcasts: isolated")
    print("Stage28/28.1 analytics and overview: isolated")
    print("Scoped legacy dashboard and cross-entity search: isolated")
    print("Stage31 subscription support actions and gateway: isolated")
    print("Core CRM user mutations: ownership-validated")
    print("Telegram traffic-source cleanup: current-bot scoped")


if __name__ == "__main__":
    main()
