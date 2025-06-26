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


class BaseServicesException(Exception):
    """Base exception class for services module"""


class ServiceObjNotFound(BaseServicesException):
    """raised when service object is not found"""


class ProvisionInstanceError(BaseServicesException):
    """raised when unable to provision a new service instance"""


class SvcInstanceNotAvailableError(BaseServicesException):
    """service instance is not available"""


class SvcInstanceDeleteError(BaseServicesException):
    """Error during deleting instance"""


class SvcInstanceNotFound(BaseServicesException):
    """service instance not found"""


class SvcAttachmentDoesNotExist(BaseServicesException):
    """remote or local service attachment does not exist"""


class UnboundSvcAttachmentDoesNotExist(BaseServicesException):
    """unbound remote or local service attachment does not exist"""


class CanNotModifyPlan(BaseServicesException):
    """remote or local service attachment already provided"""


class ReferencedAttachmentNotFound(BaseServicesException):
    """raised when trying to reference a nonexistent service attachment for sharing"""


class SharedAttachmentAlreadyExists(BaseServicesException):
    """raised when trying to create an already existed shared attachment"""


class DuplicatedServiceBoundError(BaseServicesException):
    """
    when user try to create a sharing relation for an already bound service or verse-vise. Raise this error
    """


class BindServicePlanError(Exception):
    """Unable to get the right plan object when binding a service."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


# Plan Selector Errors start


class PlanSelectorError(Exception):
    """The base error for selecting plans"""


class NoPlanFoundError(PlanSelectorError):
    """No plans found when trying to select a plan"""


class MultiplePlanFoundError(PlanSelectorError):
    """Multiple plans found when trying to select a plan"""
