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

from django.utils.translation import gettext as _

from paasng.accessories.services.utils import gen_unique_id

from .client import SentryClient
from .exceptions import (
    CreateSentryClientKeyFail,
    CreateSentryProjectFail,
    CreateSentryTeamFail,
    CreateSentryUserFail,
    FetchSentryTeamMembersFail,
)
from ..base import BaseProvider, InstanceData

logger = logging.getLogger(__name__)


class SentryProvider(BaseProvider):
    display_name = _("Sentry 通用申请服务")
    """
    Sentry 资源处理
    """

    def __init__(self, config):
        """
        service_name: k8s service name, for api
        service_port: k8s service port, for api
        token: api token, for api
        domain: access domain, for user access from frontend
        """
        self._organ = config["organization"]
        self._host = config["service_name"]
        self._port = config["service_port"]
        self._token = config["token"]
        self._domain = config["domain"]

        self.client = SentryClient(host=self._host, port=self._port, token=self._token)

    def _gen_dsn(self, client_key_info):
        service = "{host}:{port}".format(host=self._host, port=self._port)
        prefix = client_key_info["dsn_prefix"]
        projectId = client_key_info["projectId"]

        return "http://{prefix}@{service}/{projectId}".format(prefix=prefix, service=service, projectId=projectId)

    def _gen_url(self, project):
        return "http://{domain}/{organ}/{project}/".format(domain=self._domain, organ=self._organ, project=project)

    @staticmethod
    def _gen_team_slug(region, app_code):
        return "{region}_{app_code}".format(region=region, app_code=app_code)

    @staticmethod
    def _get_developers(application_id):
        from paasng.platform.applications.models import Application

        application = Application.objects.get(id=application_id)
        return application.get_developers()

    # ============ crud ============

    def create(self, params) -> InstanceData:
        # 0. params
        region = params.get("region")
        app_code = params.get("application_code")
        project_slug = params.get("engine_app_name")
        project_slug = gen_unique_id(project_slug)
        application_id = params.get("application_id")

        team_slug = self._gen_team_slug(region=region, app_code=app_code)
        developers = self._get_developers(application_id)

        # 1. create team
        if not self.client.create_team(team=team_slug):
            raise CreateSentryTeamFail("Create team error! team=%s, params=%s", team_slug, params)

        # 2. create project
        if not self.client.create_project(team=team_slug, project=project_slug):
            raise CreateSentryProjectFail(
                "Create project error! team=%s, project=%s, params=%s", team_slug, project_slug, params
            )

        # 3. create client key
        ok, client_key_info = self.client.create_project_client_key(project=project_slug)
        if not ok:
            raise CreateSentryClientKeyFail("Create ClientKey error! project=%s, params=%s", project_slug, params)

        # 4. create user and add user to team
        for username in developers:
            try:
                ok, member = self.client.create_member(username=username)
                if ok:
                    self.client.add_team_member(team=team_slug, member_id=member["id"])
            except Exception:
                logger.exception("create member or add member to team fail")
                raise CreateSentryUserFail("Create Sentry user error")

        dsn = self._gen_dsn(client_key_info)
        url = self._gen_url(project_slug)

        credentials = {"dsn": dsn}
        config = {"admin_url": url}

        return InstanceData(credentials=credentials, config=config)

    def patch(self, params):
        # 0. params
        region = params.get("region")
        app_code = params.get("application_code")
        application_id = params.get("application_id")

        team_slug = self._gen_team_slug(region=region, app_code=app_code)

        # 1. fetch team members -  members = [(1, 'name')]
        ok, members = self.client.get_team_members(team=team_slug)
        if not ok:
            raise FetchSentryTeamMembersFail("Failed to get list of existing users")

        sentry_users = [u[1] for u in members]
        developers = self._get_developers(application_id)

        # 2. add new users
        for username in developers:
            try:
                if username not in sentry_users:
                    ok, member = self.client.create_member(username=username)
                    if ok:
                        self.client.add_team_member(team=team_slug, member_id=member["id"])
            except Exception:
                logger.exception("patch: create member or add member to team fail")
                raise CreateSentryUserFail("Create Sentry user error")

        # 3. remove use from team
        removable_members = [(member_id, username) for member_id, username in members if username not in developers]
        for member_id, __ in removable_members:
            try:
                self.client.delete_team_member(team=team_slug, member_id=member_id)
            except Exception:
                logger.exception("patch: remove user from team fail")
                continue

        return True

    def delete(self, instance_data: InstanceData):
        raise NotImplementedError

    def stats(self, instance):
        raise NotImplementedError
