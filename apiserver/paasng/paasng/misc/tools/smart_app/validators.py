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


from paasng.platform.declarative.constants import AppSpecVersion
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import detect_spec_version


def validate_app_desc(meta_info: dict) -> str:
    """Validate app_desc meta info and return app_code

    :param meta_info: the meta info extracted from app_desc.yaml
    :return: the app_code extracted from meta info
    :raises DescriptionValidationError: when validation fails.
    """

    app_code = _extract_app_code(meta_info)
    _validate_market(meta_info)

    return app_code


def _extract_app_code(meta_info: dict) -> str:
    """Extract app_code from meta_info, supporting both v2 and v3 spec versions.

    :raises DescriptionValidationError: When app_code is missing in meta info.
    """

    app_data = meta_info.get("app", {})
    if not app_data:
        raise DescriptionValidationError({"app": "app_desc.yaml 中缺少 app 字段"})

    try:
        spec_version = detect_spec_version(meta_info)
    except ValueError:
        raise DescriptionValidationError({"spec_version": "无法识别 app_desc.yaml 的版本"})

    match spec_version:
        case AppSpecVersion.VER_2:
            app_code = app_data.get("bk_app_code")
        case AppSpecVersion.VER_3:
            app_code = app_data.get("bkAppCode")
        case _:
            raise DescriptionValidationError({"spec_version": "不支持的 app_desc.yaml 版本"})

    if not app_code:
        raise DescriptionValidationError({"app": "app_desc.yaml 中缺少应用 ID"})

    return app_code


def _validate_market(meta_info: dict):
    """Validate that market info exists in meta_info.

    :raises DescriptionValidationError: When market info is missing in meta info.
    """
    app_data = meta_info.get("app", {})
    if app_data.get("market") is None:
        raise DescriptionValidationError({"market": "内容不能为空"})
