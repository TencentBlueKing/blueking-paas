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
from dataclasses import dataclass, field
from typing import Dict, List

from django.conf import settings
from paas_service.base_vendor import BaseProvider, InstanceData
from paas_service.utils import WRItemList

from svc_mysql.vendor.helper import MySQLAuthorizer, MySQLEngine
from svc_mysql.vendor.tls import TLSCertificateManager
from svc_mysql.vendor.utils import gen_addons_cert_mount_path, gen_unique_id, generate_mysql_password

logger = logging.getLogger(__name__)


@dataclass
class Server:
    host: str
    port: int
    user: str
    password: str
    name: str | None = None
    tls: Dict[str, str | bool] = field(default_factory=dict)


@dataclass
class Provider(BaseProvider):
    """使用 mysql client 管理用户和数据库"""

    host: str | None = None
    port: int | None = None
    user: str | None = None
    password: str | None = None
    auth_ip_list: List[str] = field(default_factory=list)
    db_operator_template: Dict = field(default_factory=dict)
    tls: Dict[str, str] = field(default_factory=dict)
    # servers 包含多个 mysql 数据库配置
    servers: List[Dict] = field(default_factory=list)

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

    def pick_server(self, host: str | None = None) -> Server:
        """pick a single server config from available servers

        :params host: 如果指定，则必须能匹配到才返回
        """
        # 没有多个 Server 的情况
        if not self.servers:
            if host and host != self.host:
                raise ValueError(f"the only server host is {self.host}, not match with {host}")

            return Server(host=self.host, port=self.port, user=self.user, password=self.password, tls=self.tls)

        # 按照 Host 进行匹配，确保能找到对应的 Server
        if host:
            for srv in self.servers:
                if srv["host"] == host:
                    return Server(**srv)

            raise ValueError(f"no server found in self.servers for host {host}")

        # 按权重随机选择 Server
        result = WRItemList.from_json(self.servers).get()
        return Server(**result.values)

    def create(self, params: Dict) -> InstanceData:
        """创建 MySQL 数据库实例 & 授权"""
        logger.info("start create mysql addons instance...")

        server = self.pick_server()
        preferred_name = params.get("engine_app_name", "")
        # egress_info perhaps format:
        # `{"egress_ips": [<ip1>, <ip2>], "digest_version": <DIGEST_VERSION>}`
        egress_info = params.get("egress_info", "{}")
        client_hosts = set(json.loads(egress_info).get("egress_ips", self.auth_ip_list)) | set(self.auth_ip_list)

        # get_unique_id & password
        # max length of uid is 16 according to gcs mysql
        uid = gen_unique_id(preferred_name)[:16]
        db_name = uid
        db_user = uid
        db_password = generate_mysql_password(settings.PASSWORD_LENGTH, settings.PASSWORD_DICTIONARY_WORDS)

        with TLSCertificateManager(server.tls) as mgr:
            # 1. 授权 Mysql 权限
            authorizer = MySQLAuthorizer(
                host=server.host,
                port=server.port,
                user=server.user,
                password=server.password,
                name=db_name,
                ssl_options=mgr.get_django_ssl_options(),
                client_hosts=list(client_hosts),
            )
            authorizer.grant_db(user=db_user, password=db_password, db_name=db_name)

            # 2. 创建数据库
            engine = MySQLEngine(
                host=server.host,
                port=server.port,
                user=db_user,
                password=db_password,
                name=db_name,
                ssl_options=mgr.get_django_ssl_options(),
            )
            create_db_sql = self.db_operator_template["CREATE_DATABASE"].format(engine=engine)
            engine.execute(create_db_sql)

            logger.info("create mysql addons instance %s success", db_name)

        credentials = {
            "host": server.host,
            "port": server.port,
            "name": db_name,
            "user": db_user,
            "password": db_password,
        }
        ca = server.tls.get("ca")
        cert = server.tls.get("cert")
        cert_key = server.tls.get("key")

        # 添加证书路径到凭证信息中
        provider_name = "mysql"
        if ca:
            credentials["ca"] = gen_addons_cert_mount_path(provider_name, "ca.crt")

        if cert and cert_key:
            credentials["cert"] = gen_addons_cert_mount_path(provider_name, "tls.crt")
            credentials["cert_key"] = gen_addons_cert_mount_path(provider_name, "tls.key")

        # 兼容各类 True 的情况
        if server.tls.get("insecure_skip_verify") in [True, "true", "True"]:
            credentials["insecure_skip_verify"] = "true"

        return InstanceData(
            credentials=credentials,
            config={
                "provider_name": provider_name,
                "enable_tls": bool(ca or cert or cert_key),
            },
        )

    def delete(self, instance_data: InstanceData):
        """删除数据库实例 -> DROP DATABASE"""
        creds = instance_data.credentials

        logger.info("start delete mysql addons instance %s...", creds["name"])
        server = self.pick_server(creds["host"])

        with TLSCertificateManager(server.tls) as mgr:
            # 删除数据库
            engine = MySQLEngine(
                host=creds["host"],
                port=creds["port"],
                user=creds["user"],
                password=creds["password"],
                name=creds["name"],
                ssl_options=mgr.get_django_ssl_options(),
            )
            drop_db_sql = self.db_operator_template["DROP_DATABASE"].format(engine=engine)
            engine.execute(drop_db_sql)

    def patch(self, instance_data: InstanceData, params: Dict) -> InstanceData:
        raise NotImplementedError
