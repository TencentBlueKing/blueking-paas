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
import datetime
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Protocol

from attrs import define, field
from cookiecutter.main import cookiecutter
from django.conf import settings

from paasng.dev_resources.sourcectl.utils import generate_temp_dir
from paasng.pluginscenter.definitions import PluginCodeTemplate
from paasng.pluginscenter.models import PluginInstance


@define
class AlternativeVersion:
    name: str
    type: str
    revision: str
    url: str
    last_update: Optional[datetime.datetime] = None
    message: str = ""
    extra: dict = field(factory=dict)


class TemplateDownloader(Protocol):
    """插件模板下载器"""

    def download_to(self, template: PluginCodeTemplate, dest_dir: Path):
        """下载 `template` 到 `dest_dir` 目录"""


class PluginRepoInitializer(Protocol):
    """插件仓库初始化器"""

    def create_project(self, plugin: PluginInstance):
        """为插件在 VCS 服务创建源码项目"""

    def initial_repo(self, plugin: PluginInstance):
        """初始化插件代码"""


class PluginRepoAccessor(Protocol):
    """插件仓库访问器"""

    def extract_smart_revision(self, smart_revision: str) -> str:
        """将有名字的版本号（Named Version）转换成更具体的版本号, 例如，将 Git 的 master 分支转换成 SHA Commit ID

        :param smart_revision: 有名字的版本号，比如 branch:master
        """

    def list_alternative_versions(self, include_branch: bool, include_tag: bool) -> List[AlternativeVersion]:
        """列举当前所有可选的有名字的版本号，通常包括 branch, tag 等"""


class TemplateRender:
    """插件模板渲染器"""

    def __init__(self, downloader: TemplateDownloader):
        self.downloader = downloader

    def render(self, template: PluginCodeTemplate, dest_dir: Path, context: Dict):
        """渲染 `template` 到 `dest_dir` 目录"""
        with generate_temp_dir() as temp_dir, generate_temp_dir() as render_dir:
            self.downloader.download_to(template, temp_dir)
            cookiecutter(str(temp_dir), no_input=True, extra_context=context, output_dir=str(render_dir))
            items = list(render_dir.iterdir())
            if len(items) == 1:
                # 对于自带根目录的模板, 需要丢弃最外层
                items = list(items[0].iterdir())
            for item in items:
                shutil.move(str(item), str(dest_dir / item.name))


def generate_context(instance: PluginInstance):
    return {
        "project_name": instance.id,
        "app_code": instance.id,
        "plugin_desc": instance.name,
        "init_admin": instance.creator.username,
        "init_apigw_maintainer": instance.creator.username,
        "apigw_manager_url_tmpl": settings.BK_API_URL_TMPL,
        "apigw_cors_allow_origins": "''",
        "apigw_cors_allow_methods": "GET,POST,PUT,PATCH,HEAD,DELETE,OPTIONS",
        "apigw_cors_allow_headers": "Accept,Cache-Control,Content-Type,Keep-Alive,Origin,User-Agent,X-Requested-With",
    }
