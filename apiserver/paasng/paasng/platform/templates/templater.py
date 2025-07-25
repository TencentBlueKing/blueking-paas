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
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict
from urllib.parse import urlparse

from cookiecutter.main import cookiecutter
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from paasng.platform.sourcectl.source_types import get_sourcectl_type
from paasng.platform.sourcectl.utils import compress_directory, generate_temp_dir, generate_temp_file
from paasng.platform.templates.command import EnhancedTemplateCommand
from paasng.platform.templates.constants import RenderMethod, TemplateType
from paasng.platform.templates.exceptions import TmplNotExists
from paasng.platform.templates.fixtures import ProcfileFixture
from paasng.platform.templates.models import Template
from paasng.platform.templates.utils import StoreType, download_from_blob_store, uncompress_tar_to_local_path
from paasng.utils.blobstore import BlobStore, make_blob_store
from paasng.utils.file import validate_source_dir_str

if TYPE_CHECKING:
    from paasng.platform.modules.models import Module

logger = logging.getLogger(__name__)

DEFAULT_EXECUTABLE_FILES = [
    "bin/pre-compile",
    "bin/pre_compile",
    "bin/post-compile",
    "bin/post_compile",
]


@dataclass
class SourceSyncResult:
    """The result of one templated source sync procedure"""

    dest_type: str
    error: str = ""
    extra_info: Dict = field(default_factory=dict)

    def is_success(self):
        return not self.error


class TemplateRenderer:
    def __init__(self, template_name: str, context: dict):
        """模板渲染器

        @param template_name: 模板名称
        @param context: 渲染模板用的上下文数据
        """
        try:
            template: Template = Template.objects.get(name=template_name)
        except ObjectDoesNotExist:
            raise TmplNotExists(f"Template <{template_name}> does not exists")
        self.template = template
        self.context = context

    def download_from_blob_storage(self) -> Path:
        """从对象存储中下载模板代码"""
        location = self.template.blob_url
        o = urlparse(location)
        scheme, bucket, path = o.scheme.lower(), o.netloc, Path(o.path)
        logger.debug("checkout template from [%s: %s]", scheme, location)
        if scheme == "file":
            return uncompress_tar_to_local_path(path)

        if path.is_absolute():
            # Ceph RGW 不支持绝对路径
            path = path.relative_to("/")

        store_type = {"s3": StoreType.S3, "bkrepo": StoreType.BKREPO}.get(scheme)
        if not store_type:
            logger.warning("unknown protocol type: %s, url: %s", o.scheme, location)

        return download_from_blob_store(bucket, path, store_type=store_type)

    def download_from_vcs_repository(self) -> Path:
        """从代码仓库下载模板代码"""
        source_type = get_sourcectl_type(self.template.repo_type)
        # NOTE: 用户并一不定有开发框架模板代码仓库的权限，所以必须用在代码仓库中配置的公共账号下载
        repo_controller = source_type.repo_controller_class.init_by_server_config(
            self.template.repo_type, self.template.repo_url
        )

        dest_dir = Path(tempfile.mkdtemp())
        source_dir = self.template.source_dir
        if not source_dir:
            repo_controller.export(dest_dir)
        else:
            with generate_temp_dir() as tmp_export_dir:
                repo_controller.export(tmp_export_dir)

                # 验证并获取完整源路径
                real_source_dir = validate_source_dir_str(tmp_export_dir, source_dir)
                for path in real_source_dir.iterdir():
                    shutil.move(str(path), str(dest_dir / path.relative_to(real_source_dir)))
        return dest_dir

    def render_template(self, source_path: Path, target_path: Path):
        """将模板渲染到目标目录，根据模板类型使用不同的渲染引擎：

        :param source_path: 下载模板代码的路径
        :param target_path: 模板代码渲染到的路径
        """
        if self.template.render_method == RenderMethod.COOKIECUTTER.value:
            # 插件模板用 cookiecutter 渲染
            with generate_temp_dir() as render_dir:
                cookiecutter(str(source_path), no_input=True, extra_context=self.context, output_dir=str(render_dir))
                items = list(render_dir.iterdir())
                if len(items) == 1:
                    # 对于自带根目录的模板, 需要丢弃最外层
                    items = list(items[0].iterdir())
                for item in items:
                    shutil.move(str(item), str(target_path / item.name))
        else:
            command = EnhancedTemplateCommand(
                render_method=RenderMethod(self.template.render_method),
                force_executable_files=DEFAULT_EXECUTABLE_FILES,
            )
            command.handle(str(target_path), template=str(source_path), context=self.context)
            # 如果模板定义了进程配置信息，则需要手动将进程信息写到 Procfile 中
            # FIXME: 新的模板已不再使用 Procfile，仅用于兼容旧的模板
            if self.template.processes:
                ProcfileFixture(project_root=str(target_path), context=self.context).setup(
                    processes=self.template.processes
                )

    def write_to_dir(self, target_path: Path):
        """下载模板并将渲染后写入目标目录，包含以下步骤：
        - 下载模板代码到本地
        - 将模板中的变量用 context 渲染

        :param target_path: 模板代码写入的路径，是已存在的空目录
        """
        try:
            # 插件模板的代码存放在代码仓库中
            if self.template.type == TemplateType.PLUGIN:
                source_path = self.download_from_vcs_repository()
            else:
                # 模板代码默认存放在对象存储中
                source_path = self.download_from_blob_storage()

            self.render_template(source_path, target_path)
        finally:
            if "source_path" in locals() and source_path.exists():
                if source_path.is_file():
                    source_path.unlink()
                else:
                    shutil.rmtree(source_path)


def generate_initial_code(template_name: str, context: dict) -> Path:
    """生成应用的初始化模板

    :param template_name: 模板名称
    :param context: 渲染模板用的上下文数据
    :returns: 包含渲染后模板代码的临时目录路径
    :note: 该函数返回的临时目录由调用方负责清理。调用方应在使用完目录后调用`shutil.rmtree()`删除该目录，以避免临时文件堆积。目录内容在函数返回后不会被自动清理。
    """
    target_path = Path(tempfile.mkdtemp())
    renderer = TemplateRenderer(template_name, context=context)
    renderer.write_to_dir(target_path)
    return target_path


def upload_directory_to_storage(module: "Module", target_path: Path) -> SourceSyncResult:
    """将指定目录内容上传到对象存储

    :param module: 模块对象
    :param source_path: 需要上传的本地目录路径
    """
    application = module.application
    # NOTE: 把 application.region 修改为了 application.tenant_id
    key = f"app-template-instances/{application.tenant_id}/{application.code}-{module.name}.tar.gz"

    sync_procedure = BlobStoreSyncProcedure(
        blob_store=make_blob_store(bucket=settings.BLOBSTORE_BUCKET_APP_SOURCE), key=key
    )
    return sync_procedure.run(str(target_path))


def upload_init_code_to_storage(module: "Module", context: dict) -> SourceSyncResult:
    """生成初始化代码并上传到对象存储
    FIXME：目前在构建配置等页面下载初始化模板时，是调用本函数重新生成初始化代码。
    正常来说应该只要重新生成下载链接即可，可能是希望用户下载的永远是最新的框架代码，所以每次下载都要重新走初始化逻辑。

    :param module: 模块对象
    :param context: 渲染上下文数据
    """
    with generate_temp_dir() as target_path:
        renderer = TemplateRenderer(module.source_init_template, context=context)
        renderer.write_to_dir(target_path)

        return upload_directory_to_storage(module, target_path)


@dataclass
class BlobStoreSyncProcedure:
    """Sync templated source to Blob Store."""

    blob_store: BlobStore
    key: str

    downloadable_address_expires_in = 3600 * 4

    def run(self, source_path: str) -> SourceSyncResult:
        """Compress the source_path and upload the content to given key"""
        with generate_temp_file(suffix=".tar.gz") as package_path:
            logger.debug("compressing templated source, key=%s...", self.key)
            compress_directory(source_path, package_path)
            self.blob_store.upload_file(package_path, self.key, ExtraArgs={"ACL": "private"})

        # Generate a temporary accessible url for source codes
        url = self.blob_store.generate_presigned_url(key=self.key, expires_in=self.downloadable_address_expires_in)
        return SourceSyncResult(
            dest_type=self.blob_store.STORE_TYPE,
            extra_info={
                "downloadable_address": url,
                "downloadable_address_expires_in": self.downloadable_address_expires_in,
            },
        )
