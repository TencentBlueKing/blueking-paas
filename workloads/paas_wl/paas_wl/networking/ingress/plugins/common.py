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
from blue_krill.text import remove_prefix, remove_suffix

from paas_wl.networking.ingress.plugins.ingress import IngressPlugin


class SubpathCompatPlugin(IngressPlugin):
    """Plugin which maintains compatibility when app was configured to handle requests under a non-default
    subpath, responsibilities includes set proper `X-Script-Name` header(required by backend service
    for handling path).
    """

    def make_configuration_snippet(self) -> str:
        """
        Must use "configuration-snippet" instead of "server-snippet" otherwise "proxy-set-header"
        directive will stop working because it already can be found in location block.

        :raise: RuntimeError when `self.domains` has a non-standard structure
        """
        if not self.domains:
            return ''

        # "/$1$3" is the sub-path provided from platform or custom domain, for root path case, it should be "/"
        # See also: the guarantee of makeLocationPath
        return "proxy_set_header X-Script-Name /$1$3;"

    @staticmethod
    def make_rewrite_target() -> str:
        # "/$2" is the user request path to the app (without any sub-path provided from platform or custom domain)
        # See also: the guarantee of ProcessIngressSerializerRegexpRewriteMixin.get_path_pattern
        return "/$2"

    @staticmethod
    def make_location_path(path: str) -> str:
        """Get the path pattern, which should work well with `rewrite-target`

        In this function, we guarantee that:
        1. "/$2" is the user request path to the app (without any sub-path provided from platform or custom domain)
        2. "/$1$3" is the sub-path provided from platform or custom domain, for root path case,
           it should be root path "/"
        3. "/$1$3/$2" is the real request path to the ingress
        Ref: https://kubernetes.github.io/ingress-nginx/examples/rewrite/#rewrite-target

        :param path_str: The raw inputted request path, without any regular expressions
        :return: a regex path, which should work well with ingress `rewrite-target`
        """
        if path == "/":
            # for root path, we don't need any rewrite at all, but for compatible with sub-path case
            # we return the regex as below.
            # Examples:
            # - request path = "/"
            # "/$2" = "/", "/$1$3" = "/"
            # - request path = "/foo"
            # "/$2" = "/foo", "/$1$3" = "/"
            return "/()(.*)"

        trim_path = remove_prefix(path, "/")
        # use regex to rewrite request path to root, we can get sub-path from "/$1$3"
        # Examples:
        # - path = "/sub-path/", request path = "/sub-path/foo"
        # $1 = "sub-path", $2 = "foo", $3 = "", "/$1$3" = "/sub-path"
        # - path = "/sub-path", request path = "/sub-path/foo"
        # $1 = "sub-path", $2 = "foo", $3 = nil, "/$1$3" = "/sub-path"
        # - path = "/sub-path", request path ="/sub-path"
        # $1 = nil, $2 = nil, $3 = "sub-path, "/$1$3" = "/sub-path"
        # - path = "/a/b/c/d/", request path = "/a/b/c/d/e/f"
        # $1 = "/a/b/c/d", $2 = "e/f", $3 = "", "/$1$3" = "/a/b/c/d
        if trim_path.endswith("/"):
            # for the case trimPath ends with "/"
            return "/{}/(.*)()".format(remove_suffix(trim_path, "/"))
        # adapter the trimPath that ends without slash
        return "/{}/(.*)|/({}$)".format(trim_path, trim_path)

    @staticmethod
    def parse_location_path(path_pattern: str) -> str:
        """parse path_str from path pattern(which is return by make_location_path)

        >>> SubpathCompatPlugin.parse_location_path("/()(.*)")
        "/"
        >>> SubpathCompatPlugin.parse_location_path("/foo/(.*)()")
        "/foo/"
        >>> SubpathCompatPlugin.parse_location_path("/foo/bar/(.*)()")
        "/foo/bar/
        >>> SubpathCompatPlugin.parse_location_path("/foo/(.*)|/(foo)")
        "/foo"
        >>> SubpathCompatPlugin.parse_location_path("/foo/bar/(.*)|/(foo/bar)")
        "/foo/bar"
        """
        # 兼容解析旧正则表达式
        if "()(.*)" in path_pattern:
            return path_pattern[: -len("()(.*)")]
        elif "(/|$)(.*)" in path_pattern:
            return path_pattern[: -len("(/|$)(.*)")] + "/"

        if "|" not in path_pattern:
            return path_pattern[: -len("(.*)()")]
        return path_pattern[: path_pattern.index("|") - len("/(.*)")]
