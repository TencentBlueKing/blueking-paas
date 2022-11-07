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
import json
from typing import Dict

from django.forms import CharField, ChoiceField, ModelForm, Textarea

from paasng.platform.core.region import RegionType
from paasng.platform.modules.models import AppBuildPack, AppSlugBuilder, AppSlugRunner


class JSONEnvironmentFieldMixin:
    environments = CharField(widget=Textarea)
    data: Dict

    def clean_environments(self):
        return json.loads(self.data["environments"])


class AppSlugBuilderForm(ModelForm, JSONEnvironmentFieldMixin):
    region = ChoiceField(choices=RegionType.get_choices())

    class Meta(object):
        model = AppSlugBuilder
        exclude = ('updated', 'created', 'modules', 'buildpacks')


class AppSlugRunnerForm(ModelForm, JSONEnvironmentFieldMixin):
    region = ChoiceField(choices=RegionType.get_choices())

    class Meta(object):
        model = AppSlugRunner
        exclude = ('updated', 'created', 'modules')


class AppBuildPackForm(ModelForm, JSONEnvironmentFieldMixin):
    region = ChoiceField(choices=RegionType.get_choices())

    class Meta(object):
        model = AppBuildPack
        exclude = ('updated', 'created', 'modules')
