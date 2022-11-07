# -*- coding: utf-8 -*-
from unittest import mock

import pytest
from django.utils.crypto import get_random_string

from tests.utils.mocks.bcs_client import StubBCSClient

pytestmark = pytest.mark.django_db


class TestProcessViewSet:
    def test_list_processes_statuses(self, api_client, scale_url, create_release):
        assert create_release().status_code == 201
        response = api_client.get(scale_url)
        assert response.status_code == 200
        assert response.json()['count'] == 1


class TestProcessInstanceViewSet:
    @mock.patch("paas_wl.platform.system_api.views.BCSClient", new=StubBCSClient)
    def test_create_webconsole(self, bk_user, api_client, webconsole_url):
        response = api_client.post(
            webconsole_url, data={'operator': bk_user.username, 'container_name': get_random_string(8)}
        )
        data = response.data['data']
        assert data['session_id']
        assert data['web_console_url']
