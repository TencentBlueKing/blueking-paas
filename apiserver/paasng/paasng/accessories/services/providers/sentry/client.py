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

import requests

from .exceptions import RequestSentryAPIFail

logger = logging.getLogger(__name__)


class SentryClient:
    def __init__(self, host, port, token):
        # default, just one organization
        self.organization = "sentry"
        self.base_url = "http://{host}:{port}".format(host=host, port=port)
        self.headers = {"Content-Type": "application/json", "Authorization": "Bearer {token}".format(token=token)}

    def _request(self, method, path, data, timeout=10):
        url = "{base_url}{path}".format(base_url=self.base_url, path=path)
        headers = self.headers
        try:
            if method == "GET":
                resp = requests.get(url=url, headers=headers, params=data, timeout=timeout)
            elif method == "HEAD":
                resp = requests.head(url=url, headers=headers, timeout=timeout)
            elif method == "POST":
                resp = requests.post(url=url, headers=headers, json=data, timeout=timeout)
            elif method == "DELETE":
                resp = requests.delete(url=url, headers=headers, json=data)
            elif method == "PUT":
                resp = requests.put(url=url, headers=headers, json=data)
            else:
                return False, None
        except requests.exceptions.RequestException:
            logger.exception("Request sentry failed, connection exception")
            raise RequestSentryAPIFail("Request sentry failed, connection exception")

        resp_json = {}
        try:
            if resp.status_code != 204:
                resp_json = resp.json()
        except Exception:
            logger.exception("Failed to request sentry, failed to parse json")

        # 409, conflict means already created
        if resp.status_code not in (200, 201, 202, 204, 409):
            logger.exception(
                "Request sentry failed, return status is not 20X/409[method=%s, url=%s, data=%s, status=%s, resp=%s]",
                method,
                url,
                data,
                resp.status_code,
                resp_json,
            )
            return False, resp_json

        return True, resp_json

    # ================= team =================
    def create_team(self, team):
        method = "POST"
        path = "/api/0/organizations/{organization}/teams/".format(organization=self.organization)
        data = {"slug": team, "name": team}
        ok, result = self._request(method, path, data)
        return ok

    # ================= project =================
    def create_project(self, team, project):
        method = "POST"
        path = "/api/0/teams/{organization}/{team}/projects/".format(organization=self.organization, team=team)
        data = {"slug": project, "name": project}
        ok, result = self._request(method, path, data)
        return ok

    # ================= project client key =================
    def _get_client_key(self, method, path, data):
        ok, result = self._request(method, path, data)
        if ok and len(result):
            key = result[0]
            client_key_info = {
                "dsn_prefix": "{public}:{secret}".format(public=key["public"], secret=key["secret"]),
                "projectId": key["projectId"],
            }
            return True, client_key_info
        return False, None

    def if_client_key_exists(self, project):
        method = "GET"
        path = "/api/0/projects/{organization}/{project}/keys/".format(organization=self.organization, project=project)
        return self._get_client_key(method, path, {})

    def create_project_client_key(self, project):
        method = "POST"
        path = "/api/0/projects/{organization}/{project}/keys/".format(organization=self.organization, project=project)
        data = {"name": "default"}

        # if exist one, return
        is_exist, key_dict = self.if_client_key_exists(project)
        if is_exist:
            return True, key_dict

        return self._get_client_key(method, path, data)

    # ================= user =================
    def create_member(self, username):
        method = "POST"
        path = "/api/0/organizations/{organization}/members/".format(organization=self.organization)
        data = {"username": username}
        ok, result = self._request(method, path, data)
        return ok, result

    # ================= team member =================
    def _http_team_member(self, method, team, member_id):
        path = "/api/0/organizations/{organization}/members/{member_id}/teams/{team}/".format(
            organization=self.organization, member_id=member_id, team=team
        )
        ok, _ = self._request(method, path, {})
        return ok

    def add_team_member(self, team, member_id):
        method = "POST"
        return self._http_team_member(method, team, member_id)

    def delete_team_member(self, team, member_id):
        method = "DELETE"
        return self._http_team_member(method, team, member_id)

    def get_team_members(self, team):
        method = "GET"
        path = "/api/0/teams/{organization}/{team}/members/".format(organization=self.organization, team=team)
        ok, result = self._request(method, path, {})

        if ok:
            members = [(i["id"], i["user"]["name"]) for i in result if i["role"] == "member"]
            return True, members
        return False, None
