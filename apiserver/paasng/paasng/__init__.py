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
from __future__ import absolute_import, unicode_literals

import os

# Start patch sqlalchemy
# Disable useless warning messages
from sqlalchemy import util

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

try:
    # prometheus 多进程时, metrics 存放的文件夹
    os.environ.setdefault("prometheus_multiproc_dir", "prometheus")
    path = os.environ.get('prometheus_multiproc_dir')
    if path is not None:
        os.mkdir(path)
except Exception:
    pass


__all__ = ['celery_app']


orig_warn = util.warn


def warn(msg):
    """Ignore all useless warning messages"""
    # This warning message was caused by automap feature
    if msg.startswith('This declarative base already contains a class'):
        return
    return orig_warn(msg)


util.warn = warn
# End patch sqlalchemy


# Patch `cattrs` structure factory to ignore init=False field in `attrs`
# Q: Why we should ignore init=False field in attrs?
# A: TLDR: High version `cattrs` is Incompatible with `attrs`
#   ---
#   At first, `attrs` will refuse those fields marked with init=False when we call the default `__init__` function
#   > if we send a field marked with init=False, the program will raise TypeError
#   Secondly, for `cattrs=1.0`, we call cattrs.structure(obj, cl) will send all fields of obj to cl.__init__() directly
#   > we can simply regart `cattrs.structure(obj, cl)` as `cl(**obj)`
#   However, for `cattrs>1.0`, this simply logic is replaced with a code-generation function `make_dict_structure_fn`,
#   in the new function `make_dict_structure_fn`, `cattrs` will try to get all fields of `cl` from `obj`
#   but no longer ignore `KeyError` exception。
#   > The new logic is Incompatible with `attrs` now.
#   So, we should register a structure hook for cattrs default converter to ignore init=False field in `attrs`
from attrs import fields, has
from cattrs import global_converter, override
from cattrs.gen import make_dict_structure_fn

global_converter.register_structure_hook_factory(
    has,
    lambda cl: make_dict_structure_fn(
        cl, global_converter, **{a.name: override(omit=True) for a in fields(cl) if not a.init}
    ),
)
# End patch cattrs
