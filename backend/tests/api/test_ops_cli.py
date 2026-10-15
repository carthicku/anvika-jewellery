"""Operator commands: verify-integrity, verify-rls, catalogue-report, send-test-email."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import cli
from app.core.config import Settings
from app.services.email import MEMORY_OUTBOX
from app.services.ops_checks import integrity_problems
from tests.api.order_helpers import buy, level

SKU = "ANV-RG-002-12"


@contextmanager
def _use_session(db: Session) -> Iterator[Session]:
    yield db


@pytest.fixture()
def run(db: Session, settings: Settings, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setattr(cli, "_session", lambda _settings: _use_session(db))
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    return cli.main


def test_integrity_is_clean_after_real_orders_and_catches_a_manual_edit(
    client: TestClient, db: Session, run, capsys: pytest.CaptureFixture[str]
) -> None:  # type: ignore[no-untyped-def]
    buy(client, db)  # a paid order: reservation committed, stock sold, totals snapshotted
    assert run(["verify-integrity"]) == 0
    assert "Integrity: OK" in capsys.readouterr().out

    # Someone edits stock in the database without a ledger entry.
    level(db, SKU).on_hand += 1
    db.flush()
    checks = {p.check for p in integrity_problems(db)}
    assert "stock_ledger" in checks
    assert run(["verify-integrity"]) == 1
    assert f"[stock_ledger] {SKU}" in capsys.readouterr().out


def test_integrity_catches_wrong_order_totals(client: TestClient, db: Session) -> None:
    reference = buy(client, db)["order"]["reference"]
    db.execute(
        text("UPDATE orders SET grand_total = grand_total + 1 WHERE reference = :r"),
        {"r": reference},
    )
    problems = integrity_problems(db)
    assert any(p.check == "order_totals" and reference in p.detail for p in problems)


def test_rls_check(run, db: Session, capsys: pytest.CaptureFixture[str]) -> None:  # type: ignore[no-untyped-def]
    assert run(["verify-rls"]) == 0
    db.execute(text("CREATE POLICY e2e_open ON products FOR SELECT USING (true)"))
    assert run(["verify-rls"]) == 1
    assert "products: policy 'e2e_open'" in capsys.readouterr().out


def test_catalogue_report_flags_sample_products(run, capsys: pytest.CaptureFixture[str]) -> None:  # type: ignore[no-untyped-def]
    assert run(["catalogue-report"]) == 0
    assert run(["catalogue-report", "--samples"]) == 1  # the seed is sample data
    out = capsys.readouterr().out
    assert "Published SAMPLE products" in out and "everyday-gold-band" in out


def test_send_test_email_reports_honestly(run, capsys: pytest.CaptureFixture[str]) -> None:  # type: ignore[no-untyped-def]
    MEMORY_OUTBOX.clear()
    assert run(["send-test-email", "--to", "owner@example.com"]) == 0
    assert MEMORY_OUTBOX[-1]["To"] == "owner@example.com"
    out = capsys.readouterr().out
    assert "written_to_sink" in out and "NOT delivered" in out
