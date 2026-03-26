from sqlalchemy.sql.elements import TextClause

from app.api.billing import _apply_read_uncommitted_hint


class _FakeDialect:
    def __init__(self, name: str):
        self.name = name


class _FakeBind:
    def __init__(self, dialect_name: str):
        self.dialect = _FakeDialect(dialect_name)


class _FakeSession:
    def __init__(self, dialect_name: str):
        self.bind = _FakeBind(dialect_name)
        self.executed = []

    def execute(self, statement):
        self.executed.append(statement)


def test_webhook_isolation_hint_skips_non_mssql():
    session = _FakeSession("sqlite")

    _apply_read_uncommitted_hint(session)

    assert session.executed == []


def test_webhook_isolation_hint_uses_text_for_mssql():
    session = _FakeSession("mssql")

    _apply_read_uncommitted_hint(session)

    assert len(session.executed) == 1
    stmt = session.executed[0]
    assert isinstance(stmt, TextClause)
    assert str(stmt) == "SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"
