# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
# Licensed under the MIT License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
#     http://opensource.org/licenses/MIT
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.
#
# We undertake not to change the open source license (MIT license) applicable
# to the current version of the project delivered to anyone in the future.

from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from kubernetes.client.exceptions import ApiException

from paas_wl.infras.resources.base.kres import KNamespace
from paas_wl.infras.resources.kube_res.base import (
    AppEntity,
    AppEntityDeserializer,
    AppEntityManager,
    AppEntityReader,
    AppEntitySerializer,
    EntitySerializerPicker,
    GVKConfig,
)
from paas_wl.infras.resources.kube_res.exceptions import APIServerVersionIncompatible

if TYPE_CHECKING:
    from paas_wl.bk_app.applications.models import WlApp  # noqa: F401

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def test_initialize_non_applicable_type():
    class DummyObj(AppEntity):
        class Meta:
            kres_class = KNamespace
            deserializer = DummyDeserializer

    AppEntityReader(DummyObj)
    with pytest.raises(TypeError):
        AppEntityManager(DummyObj)


class DummySerializer(AppEntitySerializer):
    def serialize(self, obj, original_obj=None):
        return {"metadata": {"name": f"new-{obj.name}"}, "apiversion": self.gvk_config.preferred_apiversion}


class DummyDeserializer(AppEntityDeserializer):
    def deserialize(self, app, kube_data):
        return DummyObj(app=app, name=kube_data.metadata.name)


@dataclass
class DummyObj(AppEntity):
    name: str

    class Meta:
        kres_class = KNamespace
        serializer = DummySerializer
        deserializer = DummyDeserializer


dummy_reader: AppEntityReader[DummyObj, "WlApp"] = AppEntityReader(DummyObj)


class TestDummyReader:
    def test_watch_with_error_event(self, wl_app):
        with mock.patch.object(dummy_reader, "kres") as mocked_kres:
            mocked_kres().__enter__().ops_batch.create_watch_stream.return_value = [
                {"type": "ERROR", "raw_object": {}}
            ]
            event = next(dummy_reader.watch_by_app(wl_app, timeout_seconds=1))
            assert event.type == "ERROR"
            assert event.error_message == "Unknown"

        with mock.patch.object(dummy_reader, "kres") as mocked_kres:
            mocked_kres().__enter__().ops_batch.create_watch_stream.side_effect = ApiException(
                410, 'Expired: too old resource version: 1 (1)"'
            )
            event = next(dummy_reader.watch_by_app(wl_app, timeout_seconds=1))
            assert event.type == "ERROR"
            assert event.error_message == 'Expired: too old resource version: 1 (1)"'

    def test_watch_with_expired_exception(self, wl_app):
        with mock.patch.object(dummy_reader, "kres") as mocked_kres:
            mocked_kres().__enter__().ops_batch.create_watch_stream.side_effect = ApiException(500, "Internal error")
            with pytest.raises(ApiException):
                next(dummy_reader.watch_by_app(wl_app, timeout_seconds=1))


dummy_kmodel: AppEntityManager[DummyObj, "WlApp"] = AppEntityManager(DummyObj)


class TestDummyManager:
    def test_create(self, wl_app, resource_name):
        res = DummyObj(app=wl_app, name=resource_name)
        dummy_kmodel.create(res)
        dummy_kmodel.delete(res)


def test_version_incompatible(wl_app):
    class WrongVersionDeserializer(AppEntityDeserializer):
        # Namespace does not has below api_version
        api_version = "extensions/v1beta1"

        def deserialize(self, wl_app, kube_data):
            return DummyObj(app=wl_app, name=kube_data.metadata.name)

    @dataclass
    class WrongVersionObj(AppEntity):
        name: str

        class Meta:
            kres_class = KNamespace
            deserializer = WrongVersionDeserializer

    with pytest.raises(APIServerVersionIncompatible):
        AppEntityReader(WrongVersionObj).list_by_app(wl_app)


class TestEntitySerializerPicker:
    class PreferredSLZ(DummySerializer):
        pass

    class v1beta1SLZ(DummySerializer):
        api_version = "extensions/v1beta1"

    class v1beta2SLZ(DummySerializer):
        api_version = "apps/v1beta2"

    class v1SLZ(DummySerializer):
        api_version = "apps/v1"

    class WrongSLZ(DummySerializer):
        api_version = "apps/v3000"

    class BoomSLZ(DummySerializer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            raise APIServerVersionIncompatible("boom")

    class v1beta1BoomSLZ(v1beta1SLZ, BoomSLZ):
        pass

    @pytest.fixture(autouse=True)
    def _setup_gvk_config(self):
        self.gvk_config = GVKConfig(
            server_version="v1.8.15",
            kind="Deployment",
            preferred_apiversion="extensions/v1beta1",
            available_apiversions=["extensions/v1beta1", "apps/v1beta2", "apps/v1"],
        )

    @pytest.mark.parametrize(
        ("serializers", "expected", "message"),
        [
            ([v1beta1SLZ, v1SLZ], v1beta1SLZ, "extensions/v1beta1 preferred"),
            ([v1SLZ, v1beta1SLZ], v1SLZ, "apps/v1 preferred"),
            ([v1beta1BoomSLZ, v1SLZ], v1SLZ, "preferred exists but init failed"),
            ([v1beta2SLZ, v1SLZ], v1beta2SLZ, "preferred not exists"),
            ([WrongSLZ, v1SLZ], v1SLZ, "unsupported api version exists"),
            ([WrongSLZ, PreferredSLZ], PreferredSLZ, "default slz found"),
            ([BoomSLZ, PreferredSLZ], PreferredSLZ, "multiple default slz defined"),
        ],
    )
    def test_priority(self, serializers, expected, message):
        picker = EntitySerializerPicker(serializers)
        serializer = picker.get_transformer(DummyObj, self.gvk_config)

        assert isinstance(serializer, expected), message

    @pytest.mark.parametrize(
        "serializers",
        [
            [BoomSLZ],
            [WrongSLZ],
            [v1beta1BoomSLZ],
        ],
    )
    def test_api_version_not_supported(self, serializers):
        picker = EntitySerializerPicker(serializers)

        with pytest.raises(APIServerVersionIncompatible):
            picker.get_transformer(DummyObj, self.gvk_config)
