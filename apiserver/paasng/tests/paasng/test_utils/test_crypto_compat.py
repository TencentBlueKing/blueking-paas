# -*- coding: utf-8 -*-
# TencentBlueKing is pleased to support the open source community by making
# 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
# Copyright (C) Tencent. All rights reserved.
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

"""Keep fixed pre-upgrade ciphertext readable after the KMS SDK dependency upgrade.

The synthetic samples were generated with bk-crypto-python-sdk 3.0.0;
Fernet / SM4CTR use blue-krill 3.1.1 and base64(x * 32) as the test key.
They must remain fixed: a new-version round trip would miss format regressions.
"""

import base64

import pytest
from blue_krill.encrypt.handler import EncryptHandler

from paasng.utils.serializers import DecryptableCharField


@pytest.mark.parametrize(
    "ciphertext",
    [
        (
            "bkcrypt$gAAAAABqzu3rr_AmNDV3iw3ob0geAat2lzfhMR_JB1fDnjhsG5CazPmIX3KyAmt_tzChgbBPXwcK"
            "v-l3WfxN6xdE_3PTxmuhnp8gYlHbDhLmHJANzrESLSY="
        ),
        "sm4ctr$qMDbQ8XRDY/tfDi2CAy5qyNqpGBxk7Ny4S5W/DybDQeNyE0=",
    ],
    ids=["fernet-3.0.0", "sm4ctr-3.0.0"],
)
def test_legacy_database_ciphertext(ciphertext):
    handler = EncryptHandler(secret_key=base64.urlsafe_b64encode(b"x" * 32))

    assert handler.decrypt(ciphertext) == "hello-plan-password"


def test_legacy_sm2_frontend_ciphertext(settings):
    settings.FRONTEND_ENCRYPT_CIPHER_TYPE = "SM2"
    # Synthetic test key pair, generated with the old SDK for this fixture.
    settings.FRONTEND_ENCRYPT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoEcz1UBgi0DQgAEDd1g1Le11hAdv/J8gjWDIRyaZovb
y5/z3Uue51mrf7h07espdWBVI41W/Ec+mULvY98kjD511RPVbssUrLm8fQ==
-----END PUBLIC KEY-----
"""
    settings.FRONTEND_ENCRYPT_PRIVATE_KEY = """-----BEGIN EC PRIVATE KEY-----
MHcCAQEEIKpsuvwwe06hq7nLjMU9sbzm4SOSJ/ZTTQd8x3hqTJR7oAoGCCqBHM9V
AYItoUQDQgAEDd1g1Le11hAdv/J8gjWDIRyaZovby5/z3Uue51mrf7h07espdWBV
I41W/Ec+mULvY98kjD511RPVbssUrLm8fQ==
-----END EC PRIVATE KEY-----
"""
    value = {
        "_encrypted": True,
        "_encrypted_value": (
            "MHgCIAxP88CjP8GL9AfG7Xl8md8csGiBCncMLJUxy3tgR/NoAiAJnsgIU4sZEMyNJxq+YwWKmxF3RPj2idBQ"
            "dEf8ZhUJGAQgznbJxSzvaglfP9sLMmQqNRi/IdTDg2fhqkSGAVvp5ogEEF4d6Q3mZro4zesjKLvGs8k="
        ),
    }

    assert DecryptableCharField().run_validation(value) == "hello-中文-123"
