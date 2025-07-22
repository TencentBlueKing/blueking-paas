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

import shutil
from pathlib import Path

from paasng.bk_plugins.pluginscenter.definitions import PluginCodeTemplate
from paasng.platform.sourcectl.git.client import GitClient
from paasng.platform.sourcectl.utils import generate_temp_dir
from paasng.utils.file import validate_source_dir_str


class GitTemplateDownloader:
    """TemplateDownloader implement with git"""

    def __init__(self, client: GitClient):
        self.client = client

    def download_to(self, template: PluginCodeTemplate, dest_dir: Path):
        """下载 `template` 到 `dest_dir` 目录"""
        repo_url = template.repository

        source_dir = template.sourceDir
        with generate_temp_dir() as temp_dir:
            self.client.clone(repo_url, path=temp_dir, depth=1)
            self.client.clean_meta_info(temp_dir)

            real_source_dir = validate_source_dir_str(temp_dir, source_dir)
            for path in real_source_dir.iterdir():
                shutil.move(str(path), str(dest_dir / path.relative_to(real_source_dir)))
        return dest_dir
