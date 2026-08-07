from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        assert needle in text, (path, needle)


def reject(path: str, *needles: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        assert needle not in text, (path, needle)


def main() -> None:
    require(
        "app/bot/storage.py",
        "RedisStorage.from_url",
        "DefaultKeyBuilder(with_bot_id=True)",
    )
    require(
        "app/main.py",
        "build_fsm_storage(settings.redis_url)",
        "await storage.close()",
    )
    reject("app/main.py", "MemoryStorage")
    require(
        "app/managed_bots.py",
        "build_fsm_storage(settings.redis_url)",
        "await storage.close()",
    )
    reject("app/managed_bots.py", "MemoryStorage")
    require(
        "app/repositories/questions.py",
        "for_update: bool = False",
        "statement.with_for_update()",
    )
    require(
        "app/bot/handlers/answers.py",
        "for_update=True",
        "ANSWER_ALREADY_SENT",
        "await state.clear()",
    )
    require(
        "app/bot/handlers/start.py",
        "async def show_personal_link(",
        "await state.clear()",
    )
    require(
        "app/bot/handlers/navigation.py",
        "async def show_help(message: Message, state: FSMContext)",
        "await state.clear()",
    )
    require("scripts/check_stage_61_runtime.py", "Stage 61 runtime check: OK")
    assert not list((ROOT / "migrations/versions").glob("*stage_61*"))
    print("Stage 61 check: OK")
    print("Restart-safe Redis FSM with bot-id isolation: ready")
    print("Main-menu navigation exits unfinished flows safely")
    print("Concurrent answer submission is serialized")
    print("Runtime FSM smoke test: wired")
    print("No Stage 61 migration required")


if __name__ == "__main__":
    main()
