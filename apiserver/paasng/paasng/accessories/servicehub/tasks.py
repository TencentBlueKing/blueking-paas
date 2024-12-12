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
from collections import defaultdict

from paasng.accessories.servicehub.remote.client import RemoteServiceClient
from paasng.accessories.servicehub.remote.exceptions import RClientResponseError
from paasng.accessories.servicehub.remote.store import get_remote_store

from .models import ServiceInstance, UnboundRemoteServiceEngineAppAttachment

logger = logging.getLogger(__name__)


def clean_instances():
    # why not values_list? Because we will use deleting_instance lately
    deleting_instances = ServiceInstance.objects.filter(to_be_deleted=True)

    if not deleting_instances:
        logger.info("nothing need to clean.")
        return

    for instance in deleting_instances:
        service = instance.service
        uuid = instance.uuid
        try:
            service.delete_service_instance(instance)
        except NotImplementedError:
            logger.warning("remote service should implement delete logic")
            continue
        except Exception as e:
            # remain deleting status if provider delete failed
            logger.warning(f"delete service instance<{uuid}> failed: {e}")
            continue
        else:
            logger.info(f"instance<{uuid}> cleaned. ")


def check_is_unbound_remote_service_instance_recycled():
    store = get_remote_store()
    unbound_instances = UnboundRemoteServiceEngineAppAttachment.objects.all()

    if not unbound_instances:
        logger.info("no unbound remote instances waiting for to be recycled")
        return

    categorized_instances = defaultdict(list)
    for instance in unbound_instances:
        categorized_instances[str(instance.service_id)].append(instance)

    for service_id, instances in categorized_instances.items():
        remote_config = store.get_source_config(service_id)
        remote_client = RemoteServiceClient(remote_config)
        for instance in instances:
            try:
                remote_client.retrieve_instance(instance.service_instance_id)
            except RClientResponseError as e:
                # if not find service instance with this id, remote response http status code 404
                if e.status_code == 404:
                    instance.delete()
                    logger.info(f"unbound service instance<{instance.service_instance_id}> is recycled.")
                    continue
                logger.warning(f"retrive unbound remote service instance<{instance.service_instance_id}> failed: {e}")
            except Exception as e:
                logger.warning(f"retrive unbound remote service instance<{instance.service_instance_id}> failed: {e}")
            else:
                logger.info(f"unbound service instance<{instance.service_instance_id}> is not recycled.")
