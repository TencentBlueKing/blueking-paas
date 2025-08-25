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

from paasng.utils.moby_distribution.spec import manifest


def test_docker_schema1(docker_manifest_schema1_dict):
    assert manifest.ManifestSchema1(**docker_manifest_schema1_dict).dict() == docker_manifest_schema1_dict


def test_docker_schema2(docker_manifest_schema2_dict):
    assert (
        manifest.ManifestSchema2(**docker_manifest_schema2_dict).dict(exclude_unset=True)
        == docker_manifest_schema2_dict
    )


def test_oci_schema1(oci_manifest_schema1_dict):
    assert (
        manifest.OCIManifestSchema1(**oci_manifest_schema1_dict).dict(exclude_unset=True) == oci_manifest_schema1_dict
    )
