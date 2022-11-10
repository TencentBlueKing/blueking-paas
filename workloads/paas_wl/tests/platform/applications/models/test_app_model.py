# -*- coding: utf-8 -*-
import pytest
from django.core.exceptions import ObjectDoesNotExist

from paas_wl.platform.applications.models import Release
from tests.utils.app import release_setup

pytestmark = pytest.mark.django_db


class TestAppModel:
    def test_app_get_release(self, fake_app):
        release_setup(fake_app=fake_app)
        release_setup(
            fake_app=fake_app, build_params={"procfile": {"web": "command -x -z -y"}}, release_params={"version": 3}
        )

        release = Release.objects.get_latest(fake_app)
        previous = release.get_previous()

        assert release.version == 3
        assert previous.version == 2

    def test_first_release(self, fake_app):
        with pytest.raises(ObjectDoesNotExist):
            Release.objects.get_latest(fake_app).get_previous()
