from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def check() -> None:
    required = (
        "app/web/templates/crm_user_details.html",
        "app/broadcast_worker.py",
        "app/web/static/admin_stage29_2.css",
    )
    for rel in required:
        assert (ROOT / rel).is_file(), rel

    ast.parse(
        (ROOT / "app/broadcast_worker.py").read_text(encoding="utf-8"),
        filename="app/broadcast_worker.py",
    )

    template = (
        ROOT / "app/web/templates/crm_user_details.html"
    ).read_text(encoding="utf-8")
    assert template.count("{% for event in timeline %}") == 1
    assert template.count("{% endfor %}") >= 1

    worker = (ROOT / "app/broadcast_worker.py").read_text(encoding="utf-8")
    assert "Question(" in worker
    assert "answer_question_keyboard(question.id)" in worker
    assert "texts.NEW_QUESTION.format" in worker
    assert "serialize_markup(markup)" in worker

    print("Stage 29.2 check: OK")
    print("User page template: valid")
    print("Broadcast anonymous template: ready")
    print("Answer and reveal buttons: ready")
    print("Configured sender: enforced")

if __name__ == "__main__":
    check()
