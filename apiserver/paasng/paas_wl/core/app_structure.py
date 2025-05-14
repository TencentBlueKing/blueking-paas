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

from typing import Callable, Dict

from paas_wl.bk_app.applications.models import WlApp

_get_structure_func = None


def set_global_get_structure(func: Callable[[WlApp], Dict]):
    """Set the structure function, to be called by other higher modules."""
    global _get_structure_func
    _get_structure_func = func


def get_structure(app: WlApp) -> Dict:
    """This function provide compatibility with the field `App.structure`"""
    if _get_structure_func is None:
        raise RuntimeError("The function for getting app structure is not set.")
    return _get_structure_func(app)


def has_proc_type(app: WlApp, proc_type: str) -> bool:
    """Check if current app has a process type, e.g. "web" """
    return proc_type in get_structure(app)
