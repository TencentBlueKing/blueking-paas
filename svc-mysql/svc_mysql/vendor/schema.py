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

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PlanSchema(BaseModel):
    """服务方案配置"""

    host: Optional[str] = Field(None, description="MySQL 服务器主机地址", example="mysql.example.com")

    port: Optional[int] = Field(None, description="MySQL 服务端口号", example=3306)

    user: Optional[str] = Field(None, description="MySQL 管理员用户名", example="admin")

    password: Optional[str] = Field(
        None,
        description="MySQL 管理员密码",
        example="securepassword123",
    )

    auth_ip_list: List[str] = Field(
        default_factory=list, description="允许访问数据库的IP白名单列表", example=["192.168.1.1"]
    )

    db_operator_template: Dict = Field(
        default_factory={
            "CREATE_DATABASE": "CREATE DATABASE IF NOT EXISTS `{engine.name}` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;",
            "DROP_DATABASE": "DROP DATABASE IF EXISTS `{engine.name}`",
        },
        description="数据库操作模板配置",
        example={
            "CREATE_DATABASE": "CREATE DATABASE IF NOT EXISTS `{engine.name}` DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;",
            "DROP_DATABASE": "DROP DATABASE IF EXISTS `{engine.name}`",
        },
    )

    tls: Dict[str, str] = Field(
        default_factory=dict,
        description="TLS 配置参数",
        example={"ca": "ca_test", "cert": "cert_test", "cert_key": "cert_key_test", "insecure_skip_verify": True},
    )

    servers: List[Dict] = Field(
        default_factory=list,
        description="MySQL 服务器集群配置列表",
        example=[
            {"host": "mysql-primary.example.com", "port": 3306, "user": "repl_user", "password": "replpassword"},
            {"host": "mysql-replica.example.com", "port": 3307, "user": "readonly_user", "password": "readonlypass"},
        ],
    )
