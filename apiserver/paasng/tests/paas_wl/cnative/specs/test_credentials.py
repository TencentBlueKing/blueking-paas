# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""
from typing import Dict

import pytest
from django.db.models import ObjectDoesNotExist
from django_dynamic_fixture import G

from paas_wl.cnative.specs.constants import IMAGE_CREDENTIALS_REF_ANNO_KEY
from paas_wl.cnative.specs.credentials import get_references, validate_references
from paas_wl.cnative.specs.exceptions import InvalidImageCredentials
from paas_wl.workloads.images.models import AppImageCredential, AppUserCredential, ImageCredentialRef

pytestmark = pytest.mark.django_db(databases=["default", "workloads"])


def build_manifest(refs: Dict[str, str], processes: Dict[str, str]) -> Dict:
    return {
        "metadata": {
            "annotations": {f"{IMAGE_CREDENTIALS_REF_ANNO_KEY}.{proc}": ref_name for proc, ref_name in refs.items()}
        },
        "spec": {"processes": [{"name": name, "image": image} for name, image in processes.items()]},
    }


@pytest.mark.parametrize(
    "manifest, expected",
    [
        (build_manifest({}, {}), []),
        (build_manifest({"foo": "example"}, {}), []),
        (build_manifest({}, {"foo": "nginx:latest"}), []),
        (
            build_manifest({"foo": "example"}, {"foo": "nginx:latest"}),
            [ImageCredentialRef(image="nginx", credential_name="example")],
        ),
    ],
)
def test_get_references(manifest, expected):
    assert get_references(manifest) == expected


def test_validate_references(bk_app):
    references = [ImageCredentialRef(image="foo", credential_name="example")]
    with pytest.raises(InvalidImageCredentials):
        validate_references(bk_app, references)

    G(AppUserCredential, application_id=bk_app.id, name="example", username="username")
    validate_references(bk_app, references)


def test_save_image_credentials_missing(bk_app, bk_stag_wl_app):
    references = [ImageCredentialRef(image="foo", credential_name="example")]
    with pytest.raises(ObjectDoesNotExist):
        AppImageCredential.objects.flush_from_refs(bk_app, bk_stag_wl_app, references)


def test_save_image_credentials(bk_app, bk_stag_wl_app):
    G(AppUserCredential, application_id=bk_app.id, name="example", username="username")
    references = [ImageCredentialRef(image="foo", credential_name="example")]
    assert AppImageCredential.objects.filter(app=bk_stag_wl_app).count() == 0

    AppImageCredential.objects.flush_from_refs(bk_app, bk_stag_wl_app, references)
    assert AppImageCredential.objects.filter(app=bk_stag_wl_app).count() == 1

    references = [ImageCredentialRef(image="bar", credential_name="example")]
    AppImageCredential.objects.flush_from_refs(bk_app, bk_stag_wl_app, references)
    assert AppImageCredential.objects.filter(app=bk_stag_wl_app).count() == 1
    assert AppImageCredential.objects.get(app=bk_stag_wl_app).username == "username"
