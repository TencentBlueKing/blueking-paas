#!/usr/bin/env bash
##
## TencentBlueKing is pleased to support the open source community by making
## 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
## Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
## Licensed under the MIT License (the "License"); you may not use this file except
## in compliance with the License. You may obtain a copy of the License at
##
##     http://opensource.org/licenses/MIT
##
## Unless required by applicable law or agreed to in writing, software distributed under
## the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
## either express or implied. See the License for the specific language governing permissions and
## limitations under the License.
##
## We undertake not to change the open source license (MIT license) applicable
## to the current version of the project delivered to anyone in the future.
##

# paasng app
python paasng/manage.py encryption_migration_services --no-dry-run
python paasng/manage.py encryption_migration_sourcectl --no-dry-run
python paasng/manage.py encryption_migration_oauth2 --no-dry-run
python paasng/manage.py encryption_migration_accounts --no-dry-run

# paas_wl app
python paasng/manage.py encryption_migration_cluster --no-dry-run
python paasng/manage.py encryption_migration_ingress --no-dry-run
python paasng/manage.py encryption_migration_images --no-dry-run
