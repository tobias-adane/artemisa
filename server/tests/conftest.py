import os

import pytest

from tests.pg import prepare, unsafe_reason


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        if os.environ.get("CI"):
            # En el CI estos tests tienen que correr: un salteo en silencio no vale.
            pytest.fail("TEST_DATABASE_URL is required in CI: the Postgres tests cannot be skipped")
        pytest.skip("TEST_DATABASE_URL is not set")
    reason = unsafe_reason(url)
    if reason is not None:
        # Falla fuerte a propósito: una URL equivocada no se saltea en silencio.
        pytest.fail(f"TEST_DATABASE_URL refused: {reason}")
    prepare(url)
    return url
