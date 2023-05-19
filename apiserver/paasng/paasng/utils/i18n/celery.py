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
from contextlib import nullcontext

from celery import Task
from django.utils.translation import get_language, override


class I18nTask(Task):
    """Celery Task with django i18n context"""

    LANGUAGE_CODE_KEY = "LANGUAGE_CODE"

    def apply_async(
        self, args=None, kwargs=None, task_id=None, producer=None, link=None, link_error=None, shadow=None, **options
    ):
        headers = options.setdefault("headers", {})
        if self.LANGUAGE_CODE_KEY not in headers:
            headers[self.LANGUAGE_CODE_KEY] = get_language()
        return super().apply_async(args, kwargs, task_id, producer, link, link_error, shadow, **options)

    def __call__(self, *args, **kwargs):
        ctx = nullcontext()
        if language_code := getattr(self.request, self.LANGUAGE_CODE_KEY, None):
            ctx = override(language=language_code)
        with ctx:
            return super().__call__(*args, **kwargs)
