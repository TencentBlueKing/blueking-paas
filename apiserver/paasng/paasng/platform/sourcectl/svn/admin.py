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

"""A simple SVN client by wrapping svn command line tool"""

import contextlib
import inspect
import logging
from typing import TYPE_CHECKING, Type

from django.utils.module_loading import import_string

from paasng.platform.sourcectl.source_types import get_sourcectl_names
from paasng.platform.sourcectl.svn.server_config import get_bksvn_config

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from paasng.platform.applications.models import Application


class BaseSvnAuthClient:
    def add_user(self, account, password=""):
        raise NotImplementedError

    def reset_user(self, account, password=""):
        raise NotImplementedError

    def add_dir(self, app_code, is_create_trunk=True):
        raise NotImplementedError

    def add_group(self, code, developers):
        raise NotImplementedError

    def mod_authz(self, repo_path, is_code_private, group_name=None):
        raise NotImplementedError

    def mod_authz_common(self, repo_path, authz="r", group_or_user_name="svn_t", type_id="user"):
        raise NotImplementedError

    def del_authz(self, repo_path, user_or_group, type_id):
        raise NotImplementedError


class SvnApplicationAuthorization:
    svn_client_cls: Type[BaseSvnAuthClient]

    def __init__(self, application: "Application"):
        self.application = application
        self.svn_client = self.svn_client_cls()

    @classmethod
    def create_svn_client(cls) -> BaseSvnAuthClient:
        """Create a client object for interacting with svn server"""
        return cls.svn_client_cls()

    @property
    def group_name(self):
        return self.application.code

    @property
    def code(self):
        return self.application.code

    def initialize(self, path):
        """初始化应用SVN权限信息
        :param path 不包含通用根目录的 应用path
        """
        # 创建SVN目录
        self.svn_client.add_dir(path, False)
        self.update_developers()
        # 修改目录权限
        # `v3apps/` + `somecode-123`
        repo_path = get_bksvn_config().get_base_path() + path
        self.svn_client.mod_authz(repo_path=repo_path, group_name=self.code, is_code_private=True)

    def update_developers(self):
        """更新开发者"""
        developers = self.application.get_developers()
        self.svn_client.add_group(self.group_name, developers=";".join(developers))

    def set_paas_user_root_privilege(self, path, read=True, write=False):
        """针对根路径的平台账户权限设置
        :param path 不包含通用根目录的 应用path
        """
        privilege = "%s%s" % ("r" if read else "", "w" if write else "")
        admin_credentials = get_bksvn_config().get_admin_credentials()

        # 修改目录权限
        # `v3apps/` + `somecode-123`
        repo_path = get_bksvn_config().get_base_path() + path
        self.svn_client.mod_authz_common(
            repo_path=repo_path, group_or_user_name=admin_credentials["username"], authz=privilege
        )

    def set_paas_user_privilege(self, read=True, write=False):
        """设置paas账户的权限"""
        privilege = "%s%s" % ("r" if read else "", "w" if write else "")
        admin_credentials = get_bksvn_config().get_admin_credentials()

        # 需要保证 repo obj 已经生成
        # 由于不容易切分 app_code/module，所以这里将平台账号在每一个使用了 svn module 路径下授权
        for module in self.application.modules.filter(source_type=get_sourcectl_names().bk_svn):
            self.svn_client.mod_authz_common(
                repo_path=module.get_source_obj().get_repo_fullname(),
                group_or_user_name=admin_credentials["username"],
                authz=privilege,
            )

    def destroy(self):
        """
        下架, 删除APP的svn目录
        refer bk_paas@app_release.utils_ver.utils_txopen: delete_svn_folder
        """
        raise NotImplementedError


class SvnAuthClient4Developer(BaseSvnAuthClient):
    """供开发时使用, 模拟真实的接口"""

    @classmethod
    def mock(cls, *args, **kwargs):
        logger.debug(
            "SvnAuthClient4Developer: mock call {func_name} with: ({args}, {kwargs})".format(
                func_name=inspect.stack()[1][3], args=args, kwargs=kwargs
            )
        )

    @classmethod
    def add_user(cls, account, password=""):
        cls.mock(account=account, password=password)
        return {
            "account": account,
            "password": password,
        }

    @classmethod
    def reset_user(cls, account, password=""):
        cls.mock(account=account, password=password)
        return {
            "account": account,
            "password": password,
        }

    @classmethod
    def add_dir(cls, app_code, is_create_trunk=True):
        return cls.mock(app_code=app_code, is_create_trunk=is_create_trunk)

    @classmethod
    def add_group(cls, code, developers):
        return cls.mock(code=code, developers=developers)

    @classmethod
    def mod_authz(cls, repo_path, is_code_private, group_name=None):
        return cls.mock(repo_path=repo_path, is_code_private=is_code_private, group_name=group_name)

    @classmethod
    def mod_authz_common(cls, repo_path, authz="r", group_or_user_name="svn_t", type_id="user"):
        return cls.mock(repo_path=repo_path, authz=authz, group_or_user_name=group_or_user_name, type_id=type_id)

    @classmethod
    def del_authz(cls, repo_path, user_or_group, type_id):
        return cls.mock(repos=repo_path, user_or_group=user_or_group, type_id=type_id)


class DummyAppAuthorization(SvnApplicationAuthorization):
    """Dummy authorization type which does no real authorizations"""

    svn_client_cls = SvnAuthClient4Developer


def get_svn_authorization_manager_cls() -> Type[SvnApplicationAuthorization]:
    config = get_bksvn_config()
    if not config.auth_mgr_cls:
        return DummyAppAuthorization
    return import_string(config.auth_mgr_cls)


def get_svn_authorization_manager(application):
    cls = get_svn_authorization_manager_cls()
    return cls(application)


@contextlib.contextmanager
def promote_repo_privilege_temporary(application):
    auth_manager = get_svn_authorization_manager(application)
    try:
        auth_manager.set_paas_user_privilege(read=True, write=True)
        yield
    finally:
        auth_manager.set_paas_user_privilege(read=True, write=False)
