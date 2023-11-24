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
"""A simple SVN client by wrapping svn command line tool
"""
import contextlib
import inspect
import json
import logging
from typing import TYPE_CHECKING, Optional, Type

import requests
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _

from paasng.platform.sourcectl.source_types import get_sourcectl_names
from paasng.platform.sourcectl.svn.server_config import get_bksvn_config

from .exceptions import SVNServiceError

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from paasng.platform.applications.models import Application  # noqa


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


class BaseRealSvnAuthClient(BaseSvnAuthClient):
    REGION: str
    SVN_SECRET = "32fc6114554e3c53d5952594510021e2"
    SVN_OPERATE_ERROR_NOTIFIER = "admin"
    DUMMY = True
    TIMEOUT = 60
    SSL_VERIFY = False

    BASE_SVN_ADD_USER = "{admin_url}svn_add/user/"
    BASE_SVN_MOD_COMMON = "{admin_url}svn_mod/common/"
    BASE_SVN_MOD_GROUP = "{admin_url}svn_mod/group/"
    BASE_SVN_MOD_AUTHZ = "{admin_url}svn_mod/authz/"
    BASE_SVN_ADD_DIR = "{admin_url}svn_add/app_dir/"
    BASE_SVN_DEL_AUTHZ = "{admin_url}svn_del/authz/"

    def __init__(self):
        admin_url = self.get_admin_url(self.REGION)
        if not admin_url:
            return
        if not admin_url.endswith("/"):
            admin_url += "/"

        self.SVN_ADD_USER = self.BASE_SVN_ADD_USER.format(admin_url=admin_url)  # svn用户添加
        self.SVN_MOD_COMMON = self.BASE_SVN_MOD_COMMON.format(admin_url=admin_url)  # svn目录普通用户权限添加
        self.SVN_MOD_GROUP = self.BASE_SVN_MOD_GROUP.format(admin_url=admin_url)  # svn目录小组权限添加
        self.SVN_MOD_AUTHZ = self.BASE_SVN_MOD_AUTHZ.format(admin_url=admin_url)  # svnapp目录权限添加
        self.SVN_ADD_DIR = self.BASE_SVN_ADD_DIR.format(admin_url=admin_url)  # svn app目录添加
        self.SVN_DEL_AUTHZ = self.BASE_SVN_DEL_AUTHZ.format(admin_url=admin_url)  # svn 权限删除

    @staticmethod
    def get_admin_url(region: str) -> Optional[str]:
        try:
            return get_bksvn_config(region).admin_url
        except RuntimeError:
            logger.warning("No bk svn sourcectl was configured")
            return None

    def request(self, url, params, **kwargs):
        # 带上权限信息
        params.update({"dummy": self.DUMMY, "secret": self.SVN_SECRET})

        response = requests.get(url, params=params, timeout=self.TIMEOUT, verify=self.SSL_VERIFY, **kwargs)

        # 检查状态码
        if not (200 <= response.status_code < 300):
            logger.critical(response.content)
            message = _("SVN注册服务异常, 状态码: %s") % response.status_code
            raise SVNServiceError(message)

        result = json.loads(response.content)

        # 解析返回结果
        if not result[0]:
            raise SVNServiceError(result[1])

        return result[1]

    def add_user(self, account, password=""):
        """
        svn用户添加
        @param account: 用户名
        @return: (True, [account, passwd]) 或 (False, error_msg)
        @note: 对应替换create_svn_acct脚本，使用函数：developer_center.views.apply_svn_account
        测试点：申请开发者、app注册
        """
        kwargs = {
            "username": account,
            "passwd": password,
        }
        result = self.request(url=self.SVN_ADD_USER, params=kwargs)

        # 解析返回内容
        account, password = result.split("=")

        return {"account": account.strip(), "password": password.strip()}

    def reset_user(self, account, password=""):
        """svn重置账户密码"""
        return self.add_user(account, password)

    def add_dir(self, app_code, is_create_trunk=True):
        """
        app注册创建svn目录
        @param app_code: app编码
        @param is_create_trunk: 是否创建trunk目录，初始化代码则不需要创建
        @return: (True, right_msg) 或 (False, error_msg)
        @note: 对应替换modsvn脚本，使用函数：developer_center.views._create_db_and_svn
        测试点：app注册
        """
        kwargs = {
            "app_code": app_code,
            "is_create_trunk": is_create_trunk,
        }

        result = self.request(url=self.SVN_ADD_DIR, params=kwargs)
        return result

    def add_group(self, code, developers):
        """
        appsvn目录小组添加（初始化开发者、添加、删除开发者都走这个接口）
        @param code: app编码
        @param developers: app开发者
        @return: (True, right_msg) 或 (False, error_msg)
        @note: 对应替换modsvn脚本，使用函数：
        developer_center.views._create_db_and_svn
        developer_center.views._modify_db_info
        developer_center.utils.add_user_power_svn
        developer_center.utils.mod_user_power_svn
        测试点：app注册，app开发者修改
        """
        app_dev_list = developers.split(";")
        group_users = ",".join(app_dev_list)
        kwargs = {
            "group_name": code,
            "group_users": group_users,
        }
        result = self.request(url=self.SVN_MOD_GROUP, params=kwargs)
        return result

    def mod_authz(self, repo_path, is_code_private, group_name=None):
        """
        appsvn目录权限添加
        @param repo_path: 仓库
        @param is_code_private: 是否敏感
        @param group_name: 用户组
        @return: (True, right_msg) 或 (False, error_msg)
        @note: 对应替换modsvn脚本，使用函数：
        developer_center.views._create_db_and_svn
        developer_center.views._modify_db_info
        测试点：app注册，app开发者修改
        """
        # 所有 module 共用同一个 group
        group_name = group_name or repo_path
        kwargs = {
            "repos": repo_path,
            "priv": int(is_code_private),
            "group": group_name,
        }
        result = self.request(self.SVN_MOD_AUTHZ, params=kwargs)
        return result

    def mod_authz_common(self, repo_path, authz="r", group_or_user_name="svn_t", type_id="user"):
        """
        appsvn目录其他权限修改
        @param repo_path: repos 路径
        @param group_or_user_name: 小组名
        @param authz: 权限
        @param type_id: group/user
        @return: (True, right_msg) 或 (False, error_msg)
        @note: 对应替换modsvn脚本，使用函数：
        developer_center.views._create_db_and_svn
        developer_center.views._modify_db_info
        测试点：app注册，app开发者修改
        """
        kwargs = {
            "repos": repo_path,
            "type_id": type_id,
            "user_or_group": group_or_user_name,
            "authz": authz,
        }

        self.request(self.SVN_MOD_COMMON, params=kwargs)

    def del_authz(self, repo_path, user_or_group, type_id):
        """
        appsvn目录权限删除
        @param repo_path: repo_path 路径
        @param user_or_group: 小组或用户
        @param type_id: user/group
        @return: (True, right_msg) 或 (False, error_msg)
        @note: 对应替换modsvn脚本，使用函数：
        developer_center.views.app_delete
        测试点：删除app
        """
        kwargs = {
            "repos": repo_path,
            "user_or_group": user_or_group,
            "type_id": type_id,
        }
        self.request(self.SVN_DEL_AUTHZ, kwargs)


class IeodSvnAuthClient(BaseRealSvnAuthClient):
    """SVN用户账号注册及授权（互娱内部版）"""

    REGION = "ieod"
    BASE_SVN_ADD_DIR = "{admin_url}svn_add/app_dir_trunk/"


class SvnApplicationAuthorization:
    svn_client_cls: Type[BaseSvnAuthClient]

    def __init__(self, application: "Application"):
        self.application = application
        self.svn_client = self.svn_client_cls()

    @classmethod
    def create_svn_client(self) -> BaseSvnAuthClient:
        """Create a client object for interacting with svn server"""
        return self.svn_client_cls()

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
        repo_path = get_bksvn_config(self.application.region).get_base_path() + path
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
        admin_credentials = get_bksvn_config(self.application.region).get_admin_credentials()

        # 修改目录权限
        # `v3apps/` + `somecode-123`
        repo_path = get_bksvn_config(self.application.region).get_base_path() + path
        self.svn_client.mod_authz_common(
            repo_path=repo_path, group_or_user_name=admin_credentials["username"], authz=privilege
        )

    def set_paas_user_privilege(self, read=True, write=False):
        """设置paas账户的权限"""
        privilege = "%s%s" % ("r" if read else "", "w" if write else "")
        admin_credentials = get_bksvn_config(self.application.region).get_admin_credentials()

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


class IeodSvnApplicationAuthorization(SvnApplicationAuthorization):
    svn_client_cls = IeodSvnAuthClient


class DummyAppAuthorization(SvnApplicationAuthorization):
    """Dummy authorization type which does no real authorizations"""

    svn_client_cls = SvnAuthClient4Developer


def get_svn_authorization_manager_cls(region: str) -> Type[SvnApplicationAuthorization]:
    config = get_bksvn_config(region)
    if not config.auth_mgr_cls:
        return DummyAppAuthorization
    return import_string(config.auth_mgr_cls)


def get_svn_authorization_manager(application):
    region = application.region
    cls = get_svn_authorization_manager_cls(region)
    return cls(application)


@contextlib.contextmanager
def promote_repo_privilege_temporary(application):
    auth_manager = get_svn_authorization_manager(application)
    try:
        auth_manager.set_paas_user_privilege(read=True, write=True)
        yield
    finally:
        auth_manager.set_paas_user_privilege(read=True, write=False)
