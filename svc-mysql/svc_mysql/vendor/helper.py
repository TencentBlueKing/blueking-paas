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
import logging
import typing
from contextlib import contextmanager
from dataclasses import dataclass, field

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.utils import DEFAULT_DB_ALIAS, ConnectionHandler, DatabaseError
from django.utils.functional import cached_property
from paas_service.utils import get_node_ip
from svc_mysql.vendor import constants
from svc_mysql.vendor.exceptions import MySQLException, MySQLExecuteFailed

logger = logging.getLogger(__name__)


@dataclass
class MySQLEngine:
    host: str
    port: int
    user: str
    password: str
    name: str = ""

    def __post_init__(self):
        self.DATABASES = {
            DEFAULT_DB_ALIAS: {
                "ENGINE": "django.db.backends.mysql",
                # DON'T USE `NAME` to connect database
                "USER": self.user,
                "PASSWORD": self.password,
                "HOST": self.host,
                "PORT": self.port,
                "OPTIONS": {
                    "init_command": "SET default_storage_engine=INNODB",
                },
            }
        }

    @cached_property
    def handler(self):
        """使用 django 的 ConnectionHandler 抽象进行数据库连接"""
        return ConnectionHandler(self.DATABASES)

    @cached_property
    def db(self) -> "BaseDatabaseWrapper":
        return self.handler[DEFAULT_DB_ALIAS]

    def execute(self, sql: str, use_db=False):
        """
        执行原始 sql
        :param sql: sql字符串
        :param use_db: 当 use_db=True时, 该连接的会话是在 db 内的, 否则是处于 db 外的
        如果执行的sql需要进入 database 执行, 则需要设置 use_db=True
        :return:
        """
        with self.wrap_database_errors(), self.db.cursor() as cursor:
            logger.info(f"Mysql 正在执行 {sql}...")
            try:
                if use_db:
                    cursor.execute(f"use `{self.name}`;")
                cursor.execute(sql)
            except Exception:
                self.db.rollback()
                logger.exception("MySQL 执行 % 失败", sql)
                raise MySQLExecuteFailed(f"MySQL执行 {sql} 失败")
            else:
                self.db.commit()
            finally:
                self.db.close()
            return cursor.fetchall()

    @contextmanager
    def wrap_database_errors(self):
        """替换原始的 DatabaseError 为 MySQLException"""
        try:
            yield
        except DatabaseError as e:
            if self.db.connection is None:
                logger.exception(f"MySQL创建连接失败: {self.user, self.password, self.name}")
                raise MySQLException("MySQL创建连接失败")
            logger.exception("未知数据库异常: %s", e)
            raise MySQLException("未知数据库异常")


@dataclass
class MySQLAuthorizer(MySQLEngine):
    client_hosts: typing.List[str] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        self.db_hosts = f"{self.host}#{self.port}"

    def grant_db(
        self,
        user: str,
        password: str,
        db_name: str,
        privileges=constants.DEFAULT_PRIVILEGES,
    ):
        """
        授权通过 `username`、`password` 在指定的 `client_hosts` 访问 `db_hosts` 里的名为 `database_name` 的 db

        :param user: 需要被授权的用户名
        :param password: 需要被授权的用户的密码
        :param db_name: 需要被授权访问的数据库名称
        :param privileges: 允许的操作
        """
        logger.info("Grant privileges to user<%s>", user)
        node_ip = get_node_ip()
        if node_ip is not None and node_ip not in self.client_hosts:
            # 添加本机节点
            self.client_hosts.append(node_ip)

        with self.db.cursor() as cursor:
            for auth_ip in self.client_hosts:
                # 在 MySQL 8.0 版本中，`identified by` 语法已被弃用，需要分 2 步来完成
                create_user_sql = constants.CREATE_USER_FMT.format(
                    db_user=user,
                    auth_ip=auth_ip,
                    db_password=password,
                )
                logger.info(f"Mysql 正在执行 `{create_user_sql.replace(password, '******')}`...")
                cursor.execute(create_user_sql)

                grant_sql = constants.GRANT_SQL_FMT.format(
                    db_name=db_name,
                    db_user=user,
                    auth_ip=auth_ip,
                    privileges=privileges,
                )
                logger.info(f"Mysql 正在执行 `{grant_sql}`...")
                cursor.execute(grant_sql)
            logger.info("Mysql 正在执行 `flush privileges;`")
            cursor.execute("flush privileges;")
