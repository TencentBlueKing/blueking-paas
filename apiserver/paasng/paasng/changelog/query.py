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
import time
from pathlib import Path, PosixPath
from typing import Dict, List, Tuple

from django.conf import settings
from django.utils.translation import get_language
from packaging.version import InvalidVersion, Version, parse

logger = logging.getLogger(__name__)


class Changelog:
    """
    变更(版本)日志

    :param log_path: 版本日志存放目录. 目录下包含语言子目录, 如 /xxx/changelog/zh-cn
    """

    def __init__(self, log_path: str = settings.CHANGELOG_PATH):
        self.log_path = Path(log_path) / get_language()

    def list_versions(self) -> List[Dict[str, str]]:
        """查询版本列表"""
        if not self.log_path.is_dir():
            return []

        versions = []
        for file in self._iter_log_path():
            version, date = self._extract_version_and_date(file.stem)
            versions.append({'version': version, 'date': date})

        # 按照版本号从新到旧的排序
        versions = sorted(versions, key=lambda v: Version(v['version']), reverse=True)
        return versions

    def get_log_detail(self, version: str) -> str:
        """查询版本详情"""
        if not self.log_path.is_dir():
            return ''

        for file in self._iter_log_path():
            v, _ = self._extract_version_and_date(file.stem)
            if version == v:
                return file.read_text()

        return ''

    def _iter_log_path(self):
        """迭代目录下有效的 changelog 文件"""
        for file in self.log_path.iterdir():
            if file.is_file() and self._is_valid_file_name(file):
                yield file

    def _is_valid_file_name(self, file: PosixPath) -> bool:
        """判断 changelog 文件名是否有效.

        有效的文件名格式如 v1.1.1_2022-11-17.md
        """
        if file.suffix != '.md':
            return False

        version, date = self._extract_version_and_date(file.stem)

        try:
            parse(version)
            time.strptime(date, '%Y-%m-%d')
        except (TypeError, ValueError, InvalidVersion):
            logger.error(f'invalid file name {file.name}')
            return False
        else:
            return True

    def _extract_version_and_date(self, file_stem: str) -> Tuple[str, str]:
        """从文件名中提取出版本和日期信息"""
        version, _, date = file_stem.partition('_')
        return version, date
