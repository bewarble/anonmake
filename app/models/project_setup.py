from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ProjectProfile(Base):
    __tablename__ = "project_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(48), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    defaults: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ProjectSetupDraft(Base):
    __tablename__ = "project_setup_drafts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), index=True)
    profile_code: Mapped[str] = mapped_column(String(48), nullable=False, default="anonymous_questions")
    code: Mapped[str | None] = mapped_column(String(32), index=True)
    display_name: Mapped[str | None] = mapped_column(String(96))
    description: Mapped[str | None] = mapped_column(Text)
    telegram_username: Mapped[str | None] = mapped_column(String(64))
    telegram_bot_id: Mapped[int | None] = mapped_column(BigInteger)
    telegram_token_encrypted: Mapped[str | None] = mapped_column(Text)
    telegram_token_hint: Mapped[str | None] = mapped_column(String(32))
    telegram_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    impaya_api_url: Mapped[str | None] = mapped_column(String(512))
    impaya_api_token_encrypted: Mapped[str | None] = mapped_column(Text)
    impaya_terminal_name: Mapped[str | None] = mapped_column(String(128))
    impaya_binding_terminal_name: Mapped[str | None] = mapped_column(String(128))
    impaya_recurrent_terminal_name: Mapped[str | None] = mapped_column(String(128))
    impaya_payment_form_url_template: Mapped[str | None] = mapped_column(String(1024))
    impaya_webhook_secret_encrypted: Mapped[str | None] = mapped_column(Text)
    assigned_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), index=True)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft", index=True)
    validation_errors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    launched_bot_id: Mapped[int | None] = mapped_column(ForeignKey("bot_instances.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
