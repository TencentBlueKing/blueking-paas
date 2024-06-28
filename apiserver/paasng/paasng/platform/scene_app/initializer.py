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

import logging
from pathlib import Path
from typing import Dict, Tuple

import yaml
from django.conf import settings
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from paasng.infras.oauth2.utils import create_oauth2_client, get_oauth2_client_secret
from paasng.platform.applications.models import Application
from paasng.platform.declarative.exceptions import DescriptionValidationError
from paasng.platform.declarative.handlers import AppDescriptionHandler
from paasng.platform.modules.constants import SourceOrigin
from paasng.platform.sourcectl.connector import BlobStoreSyncProcedure, SourceSyncResult, get_repo_connector
from paasng.platform.sourcectl.utils import generate_temp_dir
from paasng.platform.templates.constants import TemplateType
from paasng.platform.templates.templater import Templater
from paasng.utils.basic import get_username_by_bkpaas_user_id
from paasng.utils.blobstore import make_blob_store

logger = logging.getLogger(__name__)


class SceneAPPInitializer:
    """场景 SaaS 应用初始化"""

    def __init__(self, user, tmpl_name: str, app_name: str, app_code: str, region: str, engine_params: Dict):
        self.user = user
        self.tmpl_name = tmpl_name
        self.app_name = app_name
        self.app_code = app_code
        self.region = region
        self.engine_params = engine_params or {}
        create_oauth2_client(self.app_code, self.region)
        self.app_secret = get_oauth2_client_secret(self.app_code, self.region)

    def execute(self) -> Tuple[Application, SourceSyncResult]:
        with generate_temp_dir() as source_dir:
            templater = Templater(
                self.tmpl_name,
                TemplateType.SCENE,
                self.region,
                get_username_by_bkpaas_user_id(self.user.pk),
                self.app_code,
                self.app_secret,
                self.app_name,
            )
            # Step 1. 下载场景模板配置 & 使用创建应用时填写的信息渲染模板
            templater.write_to_dir(source_dir)

            # Step 2. 根据应用描述文件（app_desc.yaml）创建应用 & 模块
            # 根据场景模板规范，代码包名称与模板名称一致，app_desc.yaml 文件在包根目录下
            desc_filepath = source_dir / self.tmpl_name / "app_desc.yaml"
            try:
                with open(desc_filepath, "r") as fr:
                    meta_info = yaml.full_load(fr.read())
            except (IOError, yaml.YAMLError):
                logger.exception(_("加载应用描述文件失败"))
                raise DescriptionValidationError(_("应用描述文件不存在或内容不是有效 YAML 格式"))

            desc_handler = AppDescriptionHandler(meta_info)
            with atomic():
                # 由于创建应用需要操作 v2 的数据库, 因此将事务的粒度控制在 handle_app 的维度,
                # 避免其他地方失败导致创建应用的操作回滚, 但是 v2 中 app code 已被占用的问题.
                application = desc_handler.handle_app(self.user, SourceOrigin.SCENE)

                # Step 4. 为每个模块单独绑定代码仓库信息，source_dir
                repo_type = self.engine_params.get("source_control_type", "")
                repo_url = self.engine_params.get("source_repo_url", "")
                repo_auth_info = self.engine_params.get("source_repo_auth_info")
                for module_name, module_desc in desc_handler.app_desc.modules.items():
                    connector = get_repo_connector(repo_type, application.get_module(module_name))
                    connector.bind(repo_url, source_dir=module_desc.source_dir, repo_auth_info=repo_auth_info)

            # Step 5. 上传渲染完成的源码包到对象存储，生成下载链接给到用户
            source_init_result = self._gen_downloadable_app_template(application, source_dir)

            return application, source_init_result

    def _gen_downloadable_app_template(self, application: Application, source_dir: Path) -> SourceSyncResult:
        key = f"app-template-instances/{application.region}/{application.code}.tar.gz"
        sync_procedure = BlobStoreSyncProcedure(
            blob_store=make_blob_store(bucket=settings.BLOBSTORE_BUCKET_APP_SOURCE), key=key
        )
        return sync_procedure.run(str(source_dir))
