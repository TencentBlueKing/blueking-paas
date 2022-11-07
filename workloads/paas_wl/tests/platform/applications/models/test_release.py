import pytest

from paas_wl.platform.applications.models import Release

pytestmark = pytest.mark.django_db


class TestReleaseManager:
    def test_any_successful_empty(self, app):
        assert Release.objects.any_successful(app) is False

    def test_any_successful_positive(self, app, bk_user, fake_simple_build):
        app.release_set.new(bk_user.username, build=fake_simple_build, procfile={'web': 'true'})
        assert Release.objects.any_successful(app) is True
