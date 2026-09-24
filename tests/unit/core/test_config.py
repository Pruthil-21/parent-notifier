import pytest

from parent_notifier.core.config import TESTING_SECRET_KEY, load_config


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    names = ("SECRET_KEY", "MAX_UPLOAD_MB", "SESSION_COOKIE_SECURE", "APP_TIMEZONE", "TRUST_PROXY")
    for name in (*names, "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)


def test_unknown_environment_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="Unknown environment 'staging'"):
        load_config("staging", tmp_path)


def test_testing_uses_fixed_secret_and_testing_flag(tmp_path):
    config = load_config("testing", tmp_path)
    assert config["TESTING"] is True
    assert config["SECRET_KEY"] == TESTING_SECRET_KEY


def test_production_requires_secret_key(tmp_path, monkeypatch):
    with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
        load_config("production", tmp_path)
    monkeypatch.setenv("SECRET_KEY", "from-environment")
    assert load_config("production", tmp_path)["SECRET_KEY"] == "from-environment"


def test_development_generates_and_reuses_secret_key(tmp_path):
    instance = tmp_path / "instance"
    first = load_config("development", instance)["SECRET_KEY"]
    second = load_config("development", instance)["SECRET_KEY"]
    assert len(first) == 64
    assert first == second
    assert (instance / "secret_key").read_text(encoding="utf-8") == first


def test_defaults(tmp_path):
    config = load_config("testing", tmp_path)
    assert config["MAX_CONTENT_LENGTH"] == 5 * 1024 * 1024
    assert config["APP_TIMEZONE"] == "Asia/Kolkata"
    assert config["SESSION_COOKIE_SECURE"] is False
    assert config["SESSION_COOKIE_HTTPONLY"] is True
    assert config["COLLEGE_SHORT_NAME"] == "GCET"


def test_environment_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "10")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    config = load_config("testing", tmp_path)
    assert config["MAX_CONTENT_LENGTH"] == 10 * 1024 * 1024
    assert config["SESSION_COOKIE_SECURE"] is True


def test_invalid_number_names_the_variable(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "five")
    with pytest.raises(ValueError, match="MAX_UPLOAD_MB must be a whole number"):
        load_config("testing", tmp_path)


def test_only_development_reloads_templates(tmp_path):
    assert load_config("development", tmp_path / "instance")["TEMPLATES_AUTO_RELOAD"] is True
    assert load_config("testing", tmp_path)["TEMPLATES_AUTO_RELOAD"] is False


@pytest.mark.parametrize("scheme", ["postgres", "postgresql"])
def test_supabase_addresses_use_psycopg_with_encryption(tmp_path, monkeypatch, scheme):
    host = "aws-0-ap-south-1.pooler.supabase.com:6543"
    monkeypatch.setenv("DATABASE_URL", f"{scheme}://postgres.ref:secret@{host}/postgres")
    config = load_config("testing", tmp_path)
    assert config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql+psycopg://postgres.ref:")
    options = config["SQLALCHEMY_ENGINE_OPTIONS"]
    assert options["connect_args"] == {"prepare_threshold": None, "sslmode": "require"}
    assert (options["pool_size"], options["pool_pre_ping"]) == (1, True)


def test_local_postgres_and_sqlite_need_no_extra_options(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://app:app@localhost:5432/app")
    config = load_config("testing", tmp_path)
    assert config["SQLALCHEMY_ENGINE_OPTIONS"]["connect_args"] == {"prepare_threshold": None}
    monkeypatch.delenv("DATABASE_URL")
    assert load_config("testing", tmp_path)["SQLALCHEMY_ENGINE_OPTIONS"] == {}


def test_proxy_headers_are_trusted_only_when_asked(tmp_path, monkeypatch):
    assert load_config("testing", tmp_path)["TRUST_PROXY"] is False
    monkeypatch.setenv("TRUST_PROXY", "true")
    assert load_config("testing", tmp_path)["TRUST_PROXY"] is True
