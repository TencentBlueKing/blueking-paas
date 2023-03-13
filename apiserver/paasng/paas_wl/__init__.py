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
from __future__ import absolute_import, unicode_literals

import os

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
