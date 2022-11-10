# -*- coding: utf-8 -*-
import json

import pytest
from django.utils.crypto import get_random_string

from paas_wl.resources.base.client import K8sScheduler
from paas_wl.resources.kube_res.exceptions import AppEntityNotFound
from paas_wl.utils.text import b64decode, b64encode
from paas_wl.workloads.images import constants
from paas_wl.workloads.images.entities import credentials_kmodel
from paas_wl.workloads.images.models import AppImageCredential

pytestmark = pytest.mark.django_db


@pytest.mark.ensure_k8s_namespace
class TestImageCredentialsHandler:
    def test_create_empty(self, app, scheduler_client: K8sScheduler):
        scheduler_client.ensure_image_credentials_secret(app)
        obj = credentials_kmodel.get(app, name=constants.KUBE_RESOURCE_NAME)
        assert len(obj.credentials) == 0
        assert obj.name == constants.KUBE_RESOURCE_NAME
        assert obj._kube_data.data[constants.KUBE_DATA_KEY] == b64encode('{"auths": {}}')

    def test_create(self, app, scheduler_client: K8sScheduler):
        registry = get_random_string()
        username = get_random_string()
        password = get_random_string()

        AppImageCredential.objects.create(app=app, registry=registry, username=username, password=password)

        scheduler_client.ensure_image_credentials_secret(app)
        obj = credentials_kmodel.get(app, name=constants.KUBE_RESOURCE_NAME)
        assert len(obj.credentials) == 1
        assert obj.name == constants.KUBE_RESOURCE_NAME
        assert json.loads(b64decode(obj._kube_data.data[constants.KUBE_DATA_KEY])) == {
            "auths": {
                registry: {"username": username, "password": password, "auth": b64encode(f"{username}:{password}")}
            }
        }

    def test_update(self, app, scheduler_client: K8sScheduler):
        scheduler_client.ensure_image_credentials_secret(app)
        obj = credentials_kmodel.get(app, name=constants.KUBE_RESOURCE_NAME)
        assert len(obj.credentials) == 0

        AppImageCredential.objects.create(app=app, registry="foo", username="bar", password="baz")
        scheduler_client.ensure_image_credentials_secret(app)
        obj = credentials_kmodel.get(app, name=constants.KUBE_RESOURCE_NAME)
        assert len(obj.credentials) == 1

    def test_not_found(self, app):
        with pytest.raises(AppEntityNotFound):
            credentials_kmodel.get(app, name=constants.KUBE_RESOURCE_NAME)
