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

import json
import re

import pytest
from django.test.utils import override_settings

from paasng.utils.blobstore import detect_default_blob_store, generate_s3cmd_conf, make_blob_store_env

BKREPO_CONFIG = dict(
    PROJECT="dummy-project",
    ENDPOINT="dummy://dummy.dummy",
    USERNAME="dummy-username",
    PASSWORD="dummy-password",
)

S3_CONFIG = dict(
    BLOBSTORE_S3_ACCESS_KEY="dummy-access-key",
    BLOBSTORE_S3_SECRET_KEY="dummy-secret-key",
    BLOBSTORE_S3_ENDPOINT="dummy://dummy.com",
    BLOBSTORE_S3_REGION_NAME="dummy-region",
    BLOBSTORE_S3_SIG_VERSION="s3v4",
)


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        (
            dict(**S3_CONFIG, BLOBSTORE_BKREPO_CONFIG=BKREPO_CONFIG),
            "bkrepo",
        ),
        (
            dict(**S3_CONFIG, BLOBSTORE_BKREPO_CONFIG={}),
            "s3",
        ),
    ],
)
def test_detect_default_blob_store(settings, expected):
    with override_settings(**settings):
        assert detect_default_blob_store().value == expected


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        (
            dict(
                BLOBSTORE_BUCKET_APP_SOURCE="dummy-bucket",
                BLOBSTORE_BKREPO_CONFIG=BKREPO_CONFIG,
            ),
            {
                "BKREPO_CONF": json.dumps(
                    dict(
                        endpoint="dummy://dummy.dummy/generic/",
                        project="dummy-project",
                        bucket="dummy-bucket",
                        user="dummy-username",
                        password="dummy-password",
                    )
                ),
            },
        ),
        (
            dict(**S3_CONFIG, BLOBSTORE_BKREPO_CONFIG={}),
            {
                "S3CMD_CONF": generate_s3cmd_conf(
                    endpoint="dummy://dummy.com",
                    access_key="dummy-access-key",
                    secret_key="dummy-secret-key",
                    region_name="dummy-region",
                    sig_version="s3v4",
                )
            },
        ),
        (
            dict(
                **S3_CONFIG,
                BLOBSTORE_BUCKET_APP_SOURCE="dummy-bucket",
                BLOBSTORE_BKREPO_CONFIG=BKREPO_CONFIG,
            ),
            {
                "BKREPO_CONF": json.dumps(
                    dict(
                        endpoint="dummy://dummy.dummy/generic/",
                        project="dummy-project",
                        bucket="dummy-bucket",
                        user="dummy-username",
                        password="dummy-password",
                    )
                ),
            },
        ),
    ],
)
def test_make_blob_store_env(settings, expected):
    with override_settings(**settings):
        assert make_blob_store_env() == expected


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        (
            dict(
                **S3_CONFIG,
                BLOBSTORE_BUCKET_APP_SOURCE="dummy-bucket",
                BLOBSTORE_BKREPO_CONFIG=BKREPO_CONFIG,
            ),
            [
                "BKREPO_CONF",
                r"{\"endpoint\": \"dummy://dummy\.dummy/generic/\", \"project\": \"dummy-project\", "
                r"\"bucket\": \"dummy-bucket\", "
                r"\"user\": \"dummy-username\", \"password\": \"gAAAAAB.+\"}",
            ],
        ),
        (
            dict(
                **S3_CONFIG,
                BLOBSTORE_BKREPO_CONFIG={},
            ),
            [
                "S3CMD_CONF",
                r"""# Setup endpoint
host_base = dummy\.com
host_bucket = dummy\.com
bucket_location = dummy-region
use_https = False

# Setup access keys
access_key = gAAAAAB.+
secret_key = gAAAAAB.+

# Enable S3 v4 signature APIs
signature_v2 = False""",
            ],
        ),
    ],
)
def test_make_blob_store_encrypt_env(settings, expected):
    with override_settings(**settings):
        assert re.match(expected[1], make_blob_store_env(True)[expected[0]])
