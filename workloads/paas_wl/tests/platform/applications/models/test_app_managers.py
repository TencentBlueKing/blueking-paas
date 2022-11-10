# -*- coding: utf-8 -*-
import pytest
from django.conf import settings

from paas_wl.platform.applications.models.managers import AppConfigVarManager
from paas_wl.platform.applications.models.managers.app_metadata import EngineAppMetadata
from tests.utils.app import random_fake_app

pytestmark = pytest.mark.django_db


class TestAppConfigVarManager:
    def test_app_configvar_generate(self):
        app = random_fake_app(
            force_app_info={"name": "bkapp-test_me-stag", "region": "ieod"},
            paas_app_code='test_me',
            environment='stag',
        )

        action = AppConfigVarManager(app=app)
        result = action.get_envs()
        assert result["BKPAAS_SUB_PATH"] == "/ieod-bkapp-test_me-stag/"

        result_with_process = action.get_process_envs(process_type="fake")
        assert result_with_process['BKPAAS_LOG_NAME_PREFIX'] == "ieod-bkapp-test_me-stag-fake"
        assert result_with_process['PORT'] == str(settings.CONTAINER_PORT)


class TestEngineAppMetadata:
    def test_empty_data(self):
        obj = EngineAppMetadata()
        with pytest.raises(RuntimeError):
            _ = obj.get_paas_app_code()

    def test_valid_data(self):
        obj = EngineAppMetadata(paas_app_code='foo')
        assert obj.get_paas_app_code() == 'foo'
