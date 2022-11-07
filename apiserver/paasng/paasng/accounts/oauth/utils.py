# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017-2022THL A29 Limited,
a Tencent company. All rights reserved.
Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the
specific language governing permissions and limitations under the License.

We undertake not to change the open source license (MIT license) applicable

to the current version of the project delivered to anyone in the future.
"""
from typing import TYPE_CHECKING, Iterable, Tuple

from paasng.dev_resources.sourcectl.source_types import get_sourcectl_types

if TYPE_CHECKING:
    from .backends import OAuth2Backend


def get_available_backends() -> Iterable[Tuple[str, 'OAuth2Backend']]:
    for name, type_spec in get_sourcectl_types().items():
        if type_spec.support_oauth():
            yield name, type_spec.make_oauth_backend()


def get_backend(backend_name: str) -> 'OAuth2Backend':
    for sourcectl_name, backend in get_available_backends():
        if sourcectl_name == backend_name:
            return backend

    raise ValueError(f"{backend_name} is not available")
