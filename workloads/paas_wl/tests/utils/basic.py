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
import random
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, ContextManager, Iterator

from django.conf import settings
from django.utils.crypto import get_random_string


def random_resource_name():
    """A random name used as kubernetes resource name to avoid conflict
    can also be used for application name
    """
    return 'bkapp-' + get_random_string(length=12).lower() + "-" + random.choice(["stag", "prod"])


def get_default_region():
    return settings.FOR_TESTS_DEFAULT_REGION


def __generate_temp_dir__(suffix=None) -> Iterator[Path]:
    path = None
    try:
        path = Path(tempfile.mkdtemp(suffix=suffix))
        yield path
    finally:
        if path and path and path.exists():
            shutil.rmtree(path)


generate_temp_dir: Callable[..., ContextManager[Path]] = contextmanager(__generate_temp_dir__)


def __generate_temp_file__(suffix="") -> Iterator[Path]:
    path = None
    try:
        path = Path(tempfile.mktemp(suffix=suffix))
        yield path
    finally:
        if path and path.exists():
            path.unlink()


generate_temp_file: Callable[..., ContextManager[Path]] = contextmanager(__generate_temp_file__)
