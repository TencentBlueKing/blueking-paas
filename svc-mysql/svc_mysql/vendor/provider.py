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
import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from paas_service.base_vendor import BaseProvider, InstanceData
from paas_service.utils import WRItemList, generate_password
from svc_mysql.vendor.helper import MySQLAuthorizer, MySQLEngine
from svc_mysql.vendor.utils import gen_unique_id

logger = logging.getLogger(__name__)


@dataclass
class DBCredential:
    host: str
    port: int
    user: str
    password: str
    name: Optional[str] = None


@dataclass
class Provider(BaseProvider):
    """使用 mysql client 管理用户和数据库"""

    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    servers: List = field(default_factory=list)
    auth_ip_list: List[str] = field(default_factory=list)
    db_operator_template: Dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.servers and not (self.host and self.port and self.user and self.password):
            raise ValueError("config is not valid, no servers found")
        self.db_operator_template.setdefault(
            "CREATE_DATABASE",
            # default create database sql;
            "CREATE DATABASE IF NOT EXISTS `{engine.name}` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;",
        )
        self.db_operator_template.setdefault(
            "DROP_DATABASE",
            # default drop database sql;
            "DROP DATABASE IF EXISTS `{engine.name}`",
        )

    def pick_server(self) -> DBCredential:
        """pick a single server config from available servers

        :returns: (host, port)
        """
        if not self.servers:
            assert self.host, "未设置 mysql 服务地址"
            assert self.port, "未设置 mysql 服务端口"
            assert self.user, "未设置 mysql 管理员用户账号"
            assert self.password, "未设置 mysql 管理员用户密码"
            return DBCredential(host=self.host, port=self.port, user=self.user, password=self.password)

        result = WRItemList.from_json(self.servers).get()
        return DBCredential(**result.values)

    def create(self, params: Dict) -> InstanceData:
        """创建 MySQL 数据库实例
        1. 授权 Mysql 权限
        2. 创建 Database

        :param params: Dict, 由 v3 申请增强服务实例时透传
        engine_app_name: str
        auth_ip_list: List[str], default: self.auth_ip_list
        :return: InstanceData
        credentials:
            host: str
            port: int
            name: str
            user: str
            password: str
        config: {}
        """
        logger.info("正在创建增强服务实例...")
        server_credential = self.pick_server()
        preferred_name = params.get("engine_app_name", "")
        # egress_info perhaps look like: `{"egress_ips": [<IP>, ], "digest_version": <DIGEST_VERSION>}`
        egress_info = params.get("egress_info", "{}")
        client_hosts = set(json.loads(egress_info).get("egress_ips", self.auth_ip_list)) | set(self.auth_ip_list)

        # get_unique_id & password
        # max length of uid is 16 according to gcs mysql
        uid = gen_unique_id(preferred_name)[:16]
        database_name = uid
        database_user = uid

        database_password = generate_password()

        db_info = DBCredential(
            host=server_credential.host,
            port=server_credential.port,
            name=database_name,
            user=database_user,
            password=database_password,
        )

        # 1. 授权 Mysql 权限
        authorizer = MySQLAuthorizer(
            host=server_credential.host,
            port=server_credential.port,
            user=server_credential.user,
            password=server_credential.password,
            client_hosts=list(client_hosts),
        )
        authorizer.grant_db(user=db_info.user, password=db_info.password, db_name=str(db_info.name))

        # 2. 创建 DataBase
        engine = MySQLEngine(**asdict(db_info))
        create_db_sql = self.db_operator_template["CREATE_DATABASE"].format(engine=engine)
        engine.execute(create_db_sql)
        return InstanceData(credentials=asdict(db_info), config={})

    def delete(self, instance_data: InstanceData):
        """删除数据库实例, DROP DATABASE

        :param instance_data:
        credentials:
            host: str
            port: int
            name: str
            user: str
            password: str
        config: {}
        :return:
        """
        logger.info("正在删除增强服务实例...")
        db_info = instance_data.credentials
        engine = MySQLEngine(**db_info)
        drop_db_sql = self.db_operator_template["DROP_DATABASE"].format(engine=engine)
        engine.execute(drop_db_sql)

    def patch(self, instance_data: InstanceData, params: Dict) -> InstanceData:
        raise NotImplementedError
