import pytest

from paas_wl.networking.entrance.utils import get_legacy_url

pytestmark = pytest.mark.django_db


def test_get_legacy_url(bk_stag_env):
    url = get_legacy_url(bk_stag_env)
    assert url is not None
    assert len(url) > 0
