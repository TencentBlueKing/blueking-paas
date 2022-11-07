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
import logging
import re
from contextlib import contextmanager
from typing import List, Optional

from django.contrib.admindocs import views as admindoc_views
from drf_yasg.generators import EndpointEnumerator as _EndpointEnumerator
from drf_yasg.generators import OpenAPISchemaGenerator as _OpenAPISchemaGenerator

logger = logging.getLogger(__name__)


@contextmanager
def patch_replace_unnamed_groups():
    """
    patch django.contrib.admindocs.views.replace_unnamed_groups, 使其忽略正则中的未命名组
    """
    replace_unnamed_groups = admindoc_views.replace_unnamed_groups
    # 仅去除正则表达式中, 未命名分组的括号
    admindoc_views.replace_unnamed_groups = lambda x: x.replace("(", "").replace(")", "")
    yield
    admindoc_views.replace_unnamed_groups = replace_unnamed_groups


class EndpointEnumerator(_EndpointEnumerator):
    def get_path_from_regex(self, path_regex: str):
        """
        兼容嵌套在括号内的命名变量
        """
        path = super().get_path_from_regex(path_regex)
        variables = self.get_variables_from_path(path)
        if variables is None:
            # 如果路径无变量, 直接使用原值
            return path
        pattern = re.compile(path_regex)
        if len(variables) == pattern.groups:
            # 如果变量数和正则表达式分组数一致, 说明没有嵌套在括号(分组)内的命名变量, 直接使用原值
            return path

        with patch_replace_unnamed_groups():
            return super().get_path_from_regex(path_regex)

    @staticmethod
    def get_variables_from_path(path: str) -> Optional[List[str]]:
        """
        返回 path 中含有多少个变量
        """
        variables = []
        var_start = None
        for i, char in enumerate(path):
            if char == "{":
                if var_start is not None:
                    logger.warning("nested var is unsupported!")
                    return None
                var_start = i + 1
            if char == "}" and var_start is not None:
                variables.append(path[var_start:i])
                var_start = None
        if var_start is not None:
            logger.warning("var is not closed!")
            return None
        return variables


class OpenAPISchemaGenerator(_OpenAPISchemaGenerator):
    endpoint_enumerator_class = EndpointEnumerator
