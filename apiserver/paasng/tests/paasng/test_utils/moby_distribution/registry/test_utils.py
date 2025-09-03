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

import os
from typing import List
from unittest import mock

import pytest
from pydantic import BaseModel, validator

from paasng.utils.moby_distribution.registry.utils import (
    LazyProxy,
    NamedImage,
    get_private_key,
    parse_image,
    validate_media_type,
)


@pytest.fixture(autouse=True)
def restore_envs():
    backup = os.environ.copy()

    yield
    for k in set(os.environ.keys()) - set(backup.keys()):
        del os.environ[k]

    for k, v in backup.items():
        os.environ[k] = v


@pytest.fixture
def mock_generate_private_key():
    with mock.patch("paasng.utils.moby_distribution.registry.utils.ec_key.generate_private_key") as m:
        m().to_jwk.return_value = None
        yield


@pytest.mark.parametrize(
    ("envs", "expected"),
    [
        (
            {
                "MOBY_DISTRIBUTION_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgWjbKt2XZJvGHvaGy\n3593/Nljig+2yJT1z/RbaoT6VJShRANCAAQZjYo3qXEFqLBvLNbnMLWG6dFJb1bk\nyZsiBfdncuIR1zAxgpeICdsaLjGVM8IfFM0lB/XzLT7oorzv/lRCeNXD\n-----END PRIVATE KEY-----\n"
            },
            {
                "kty": "EC",
                "kid": "TIP5:NSTB:WH2C:JMZZ:KXP7:ZRUZ:6GPT:CMAP:WF32:DHSJ:7CSZ:7MQE",
                "crv": "P-256",
                "x": "GY2KN6lxBaiwbyzW5zC1hunRSW9W5MmbIgX3Z3LiEdc",
                "y": "MDGCl4gJ2xouMZUzwh8UzSUH9fMtPuiivO_-VEJ41cM",
                "d": "WjbKt2XZJvGHvaGy3593_Nljig-2yJT1z_RbaoT6VJQ",
            },
        ),
        (
            {
                "MOBY_DISTRIBUTION_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\nMIIBVQIBADANBgkqhkiG9w0BAQEFAASCAT8wggE7AgEAAkEAwi+0OuEjBdVxP4MY\nOzf561GqBvnL7ugfrqEeGmRqYG+/I2PD07a2WeafK7xqfy4Fn6d0g2c7NL85zz+X\nUr+NewIDAQABAkEAuZZ0Dw3athmfaY72GqrN7WwYLyCQGl244eJUbe7oiA66eegN\n5mz6FYe1Hr3+njsJbqkEyXWavB/yPjplviKYIQIhAOP2ICxEr3h5RF55ufJ6z02l\nB0l9ndGKBur4dVA1j/mrAiEA2hIYLL8mscqrkZ2MfbriUZzpw5Dv4FfVWp8i+DNo\nC3ECIFmFycK4wpQ0Q2Y6tYyFMC4U1hTFURn985OJOUDjmAP7AiAEopfS86kt5EHr\nUW74CS3gUDaDyqPen99QEsvafLU8cQIhAJvP/YoJPh34ySd9tk01P6tcGO6oggZR\nFbjuVcEHj5bM\n-----END PRIVATE KEY-----\n"
            },
            {
                "kty": "RSA",
                "kid": "BCP4:AAX2:CAKW:SM4X:XHIG:DVA5:3ZIQ:MFO7:DG3Q:3FKB:6ACJ:GRI5",
                "n": "wi-0OuEjBdVxP4MYOzf561GqBvnL7ugfrqEeGmRqYG-_I2PD07a2WeafK7xqfy4Fn6d0g2c7NL85zz-XUr-New",
                "e": "AQAB",
                "d": "uZZ0Dw3athmfaY72GqrN7WwYLyCQGl244eJUbe7oiA66eegN5mz6FYe1Hr3-njsJbqkEyXWavB_yPjplviKYIQ",
                "p": "4_YgLESveHlEXnm58nrPTaUHSX2d0YoG6vh1UDWP-as",
                "q": "2hIYLL8mscqrkZ2MfbriUZzpw5Dv4FfVWp8i-DNoC3E",
                "dp": "WYXJwrjClDRDZjq1jIUwLhTWFMVRGf3zk4k5QOOYA_s",
                "dq": "BKKX0vOpLeRB61Fu-Akt4FA2g8qj3p_fUBLL2ny1PHE",
                "qi": "m8_9igk-HfjJJ322TTU_q1wY7qiCBlEVuO5VwQePlsw",
            },
        ),
        (
            {},
            None,
        ),
    ],
)
def test_get_private_key(envs, expected, mock_generate_private_key):
    for k, v in envs.items():
        os.environ[k] = v

    assert get_private_key().to_jwk() == expected


class TestLazyProxy:
    def test(self):
        m = mock.MagicMock()
        proxy = LazyProxy(lambda: m)

        proxy.get()  # type: ignore[attr-defined]

        assert m.get.called


class TestValidateMediaType:
    def test_single(self):
        class T(BaseModel):
            mediaType: str

            @staticmethod
            def content_type() -> str:
                return "T"

            _validate_media_type = validator("mediaType", allow_reuse=True)(validate_media_type)

        with pytest.raises(ValueError, match="unknown media type 'a'"):
            T(mediaType="a")

        assert T(mediaType="T").mediaType == T.content_type()

    def test_multiple(self):
        class T(BaseModel):
            mediaType: str

            @staticmethod
            def content_types() -> List[str]:
                return ["T", "t"]

            _validate_media_type = validator("mediaType", allow_reuse=True)(validate_media_type)

        with pytest.raises(ValueError, match="unknown media type 'a'"):
            T(mediaType="a")

        assert T(mediaType="T").mediaType == "T"
        assert T(mediaType="t").mediaType == "t"


@pytest.mark.parametrize(
    ("image", "default_registry", "expected"),
    [
        ("python", "docker.io", NamedImage(domain="docker.io", name="library/python", tag=None)),
        ("python:latest", "docker.io", NamedImage(domain="docker.io", name="library/python", tag="latest")),
        ("docker.io/python:latest", "docker.io", NamedImage(domain="docker.io", name="library/python", tag="latest")),
        ("localhost:5000/python", "docker.io", NamedImage(domain="localhost:5000", name="python", tag=None)),
        (
            "localhost:5000/python:latest",
            "docker.io",
            NamedImage(domain="localhost:5000", name="python", tag="latest"),
        ),
        (
            "docker.io:5000/python:latest",
            "not-docker.io",
            NamedImage(domain="docker.io:5000", name="python", tag="latest"),
        ),
    ],
)
def test_parse_image(image, default_registry, expected):
    assert parse_image(image, default_registry) == expected
