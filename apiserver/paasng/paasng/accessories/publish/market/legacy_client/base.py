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
from paasng.core.core.storages.sqlalchemy import legacy_db

# TODO: 直接从 legacydb 模块里拿
LApplication = legacy_db.get_model("app_app")
LAppDevelopTimeRecored = legacy_db.get_model("app_develop_time_record")
LAppReleaseRecored = legacy_db.get_model("paas_app_release_record")
LAppBizCC = legacy_db.get_model("app_business_cc")
LAppBizCCRel = legacy_db.get_model("app_app_business_cc")
LAppGroup = legacy_db.get_model("app_app_group")
# 权限审批相关
LPlatformApprovalAdmin = legacy_db.get_model("bk_approval_approval_admin")
LPlatformApprovalApplyRecord = legacy_db.get_model("bk_approval_apply_record")
LAccessControlWhileListApplyRecord = legacy_db.get_model("access_control_wl_apply_record")
