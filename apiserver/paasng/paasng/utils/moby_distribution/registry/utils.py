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

import logging
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, ContextManager, Iterator, NamedTuple, Optional, Tuple, Union
from urllib.parse import urlparse

import libtrust
from libtrust.keys import ec_key, rs_key

logger = logging.getLogger(__name__)
client_default_timeout = float("-inf")
TypeTimeout = Optional[Union[Tuple[float, float], float]]


def get_private_key() -> Union[libtrust.ECPrivateKey, libtrust.RSAPrivateKey]:
    key = os.getenv("MOBY_DISTRIBUTION_PRIVATE_KEY")
    password = os.getenv("MOBY_DISTRIBUTION_PRIVATE_KEY_PASSWORD")
    if key is not None:
        try:
            return ec_key.ECPrivateKey.from_pem(key, password)
        except Exception:
            try:
                return rs_key.RSAPrivateKey.from_pem(key, password)
            except Exception:
                logger.warning("Unknown private key.")
    return ec_key.generate_private_key()


def validate_media_type(cls, media_type: str) -> str:
    if hasattr(cls, "content_type") and cls.content_type() != media_type:
        raise ValueError("unknown media type '{}'".format(media_type))

    if hasattr(cls, "content_types") and media_type not in cls.content_types():
        raise ValueError("unknown media type '{}'".format(media_type))

    return media_type


def new_method_proxy(func):
    def inner(self, *args):
        if "_wrapped" not in self.__dict__:
            self.__dict__["_wrapped"] = self.__dict__["_factory"]()
        return func(self._wrapped, *args)

    return inner


class LazyProxy:
    def __init__(self, obj: Callable[..., Any]):
        self.__dict__["_factory"] = obj

    __getattr__ = new_method_proxy(getattr)
    __setattr__ = new_method_proxy(setattr)
    __dir__ = new_method_proxy(dir)

    def __repr__(self):
        return repr(self.__dict__["_wrapped"])


def _generate_temp_dir(suffix=None) -> Iterator[Path]:
    path = None
    try:
        path = Path(tempfile.mkdtemp(suffix=suffix))
        logger.debug("Generating temp path: %s", path)
        yield path
    finally:
        if path and path.exists():
            shutil.rmtree(path)


generate_temp_dir: Callable[..., ContextManager[Path]] = contextmanager(_generate_temp_dir)


class NamedImage(NamedTuple):
    domain: str
    name: str
    tag: Optional[str] = None


def parse_image(image: str, default_registry: Optional[str] = None) -> NamedImage:
    """parse the `repository:tag` as NamedImage

    Usage:
    >>> parse_image("python", default_registry="docker.io")
    NamedImage(domain='docker.io', name='library/python', tag=None)

    >>> parse_image("python:latest", default_registry="docker.io")
    NamedImage(domain='docker.io', name='library/python', tag="latest")

    >>> parse_image("localhost:5000/python", default_registry="docker.io")
    NamedImage(domain='localhost:5000', name='python', tag=None)

    >>> parse_image("localhost:5000/python:latest", default_registry="docker.io")
    NamedImage(domain='localhost:5000', name='python', tag='latest')

    >>> parse_image("docker.io:5000/python:latest", default_registry="not-docker.io")
    NamedImage(domain='docker.io:5000', name='python', tag='latest')
    """
    from paasng.utils.moby_distribution.registry.client import default_client

    i = image.find("/")
    default_registry = default_registry or urlparse(default_client.api_base_url).netloc
    tag: Optional[str] = None

    # case for image in default registry
    if i == -1 or (("." not in image[:i] and ":" not in image[:i]) and image[:i] != "localhost"):
        domain = default_registry
        remainder = image
    else:
        domain = image[:i]
        remainder = image[i + 1 :]

    if ":" in remainder:
        name, tag = remainder.split(":", 1)
    else:
        name = remainder

    if domain == default_registry and "/" not in name:
        name = f"library/{name}"

    return NamedImage(domain=domain, name=name, tag=tag)
