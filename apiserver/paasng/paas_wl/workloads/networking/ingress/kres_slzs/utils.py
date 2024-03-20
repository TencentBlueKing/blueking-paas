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
import re
from dataclasses import dataclass
from textwrap import dedent
from typing import List, Optional, Tuple

from blue_krill.text import remove_prefix, remove_suffix
from django.conf import settings
from kubernetes.dynamic import ResourceInstance

from paas_wl.infras.cluster.constants import ClusterFeatureFlag
from paas_wl.infras.cluster.models import Cluster


class IngressNginxAdaptor:
    """An Adaptor shield different versions(0.20.0 ~ 0.51.0) of the ingress-nginx-controller implementation
    Note: IngressNginxAdaptor only work for Ingress api version in ["extensions/v1beta1", "networking.k8s.io/v1beta1"]

    :param cluster: The k8s cluster where the ingress will be applied to
    """

    def __init__(self, cluster: "Cluster"):
        self.cluster = cluster
        self.use_regex = self.cluster.has_feature_flag(ClusterFeatureFlag.INGRESS_USE_REGEX)

    def make_configuration_snippet(self, fallback_script_name: Optional[str] = "") -> str:
        """Make configuration snippet which set X-Script-Name as the sub-path provided by platform or custom domain

        Must use "configuration-snippet" instead of "server-snippet" otherwise "proxy-set-header"
        directive will stop working because it already can be found in location block.
        """
        if not self.use_regex:
            return LegacyNginxRewrittenProvider().make_configuration_snippet(fallback_script_name)
        return NginxRegexRewrittenProvider().make_configuration_snippet()

    def build_http_path(self, path_str: str) -> str:
        """build the http path, which is compatible with `rewrite-target` for all version nginx-ingress-controller

        To be compatible with `rewrite-target` nginx-ingress-controller >=0.22, the http path should be a pattern
        Ref: https://kubernetes.github.io/ingress-nginx/examples/rewrite/#rewrite-target
        """
        if not self.use_regex:
            return LegacyNginxRewrittenProvider().make_location_path(path_str)
        return NginxRegexRewrittenProvider().make_location_path(path_str)

    def build_rewrite_target(self) -> str:
        """build the rewrite target which will rewrite all request to sub-path provided by platform or custom domain

        In Version 0.22.0 +, any substrings within the request URI that need to be passed to the rewritten path
        must explicitly be defined in a capture group.
        Ref: https://kubernetes.github.io/ingress-nginx/examples/rewrite/#rewrite-target
        """
        if not self.use_regex:
            return LegacyNginxRewrittenProvider().make_rewrite_target()
        return NginxRegexRewrittenProvider().make_rewrite_target()

    def parse_http_path(self, pattern_or_path: str) -> str:
        """parse path_str from path pattern(which is return by build_http_path)"""
        if not self.use_regex:
            return LegacyNginxRewrittenProvider().parse_location_path(pattern_or_path)
        return NginxRegexRewrittenProvider().parse_location_path(pattern_or_path)


class LegacyNginxRewrittenProvider:
    """Maintains compatibility for ingress-nginx <= 0.21.0"""

    @staticmethod
    def make_configuration_snippet(fallback_script_name: Optional[str] = "") -> str:
        """Make configuration snippet which set X-Script-Name as the sub-path provided by platform or custom domain

        Must use "configuration-snippet" instead of "server-snippet" otherwise "proxy-set-header"
        directive will stop working because it already can be found in location block.
        """
        # `$location_path` was a variable set by ingress-controller which lives in `location` block ,
        # it's value equals `rules.https?.paths[].path` in the ingress's specification, we will use it
        # as the `Script-Name` for application.
        #
        # Which means while a domain might have many different paths, the `Script-Name` will always
        # be determined by the requests path. For example:
        #
        # - when user requests '/prod--default--foo/something', which matches `/prod--default--foo/` location,
        #   the `X-Script-Name` would be set to `/prod--default--foo/`
        # - when user requests '/foo/something', which matches `/foo/` location, `X-Script-Name` will be `/foo/`
        #
        # However, `$location_path` was added in version 0.16.0
        # For forward compatibility, we should set $location_path to shortest_path as fallback.
        # To know "How the fallback work", see also: [nginx-variables-variable-scope](https://openresty.org/download/agentzh-nginx-tutorials-en.html#nginx-variables-variable-scope)

        snippet = dedent(
            f"""\
        if ($location_path = '') {{
            set $location_path "{fallback_script_name}";
        }}

        proxy_set_header X-Script-Name $location_path;
        """
        )
        return snippet

    @staticmethod
    def make_location_path(path_str: str) -> str:
        """Get the path pattern, which should work well with `rewrite-target`"""
        if not settings.APP_INGRESS_EXT_V1BETA1_PATH_TRAILING_SLASH:
            path_str = path_str.rstrip("/")
        return path_str

    @staticmethod
    def make_rewrite_target() -> str:
        """build the rewrite target which will rewrite all request to sub-path provided by platform or custom domain

        In Version <= 0.21.0, set rewrite-target to "/" will always rewrite to root
        """
        return "/"

    @staticmethod
    def parse_location_path(location_path) -> str:
        """parse IngressRule.Path to the real path, In Version <= 0.21.0, return it directly"""
        return location_path


class NginxRegexRewrittenProvider:
    """Maintains compatibility for ingress-nginx >= 0.22.0, which use pattern in rewrite-target

    In Version 0.22.0 +, any substrings within the request URI that need to be passed to the rewritten path
    must explicitly be defined in a capture group.
    Ref: https://kubernetes.github.io/ingress-nginx/examples/rewrite/#rewrite-target
    """

    @staticmethod
    def make_configuration_snippet() -> str:
        """Make configuration snippet which set X-Script-Name as the sub-path provided by platform or custom domain

        Must use "configuration-snippet" instead of "server-snippet" otherwise "proxy-set-header"
        directive will stop working because it already can be found in location block.
        """
        # "/$1$3" is the sub-path provided by platform or custom domain, for root path case, it should be "/"
        # See also: the guarantee of make_location_path
        return "proxy_set_header X-Script-Name /$1$3;"

    @staticmethod
    def make_rewrite_target() -> str:
        # "/$2" is the user request path to the app (without any sub-path provided by platform or custom domain)
        # See also: the guarantee of ProcessIngressSerializerRegexpRewriteMixin.get_path_pattern
        return "/$2"

    @staticmethod
    def make_location_path(path: str) -> str:
        """Get the path pattern, which should work well with `rewrite-target`

        In this function, we guarantee that:
        1. "/$2" is the user request path to the app (without any sub-path provided by platform or custom domain)
        2. "/$1$3" is the sub-path provided by platform or custom domain, for root path case,
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
        # $1 = nil, $2 = nil, $3 = "sub-path", "/$1$3" = "/sub-path"
        # - path = "/a/b/c/d/", request path = "/a/b/c/d/e/f"
        # $1 = "/a/b/c/d", $2 = "e/f", $3 = "", "/$1$3" = "/a/b/c/d"
        if trim_path.endswith("/") and settings.APP_INGRESS_V1_PATH_TRAILING_SLASH:
            # for the case trimPath ends with "/"
            return "/({})/(.*)()".format(remove_suffix(trim_path, "/"))

        # adapter the trimPath that ends without slash
        # if trim_path ends with "/", remove it
        trim_path = remove_suffix(trim_path, "/")
        return "/({})/(.*)|/({}$)".format(trim_path, trim_path)

    @staticmethod
    def parse_location_path(path_pattern: str) -> str:
        """parse path_str from path pattern(which is return by make_location_path)

        >>> NginxRegexRewrittenProvider.parse_location_path("/()(.*)")
        "/"
        >>> NginxRegexRewrittenProvider.parse_location_path("/(foo)/(.*)()")
        "/foo/"
        >>> NginxRegexRewrittenProvider.parse_location_path("/(foo/bar)/(.*)()")
        "/foo/bar/
        >>> NginxRegexRewrittenProvider.parse_location_path("/(foo)/(.*)|/(foo)")
        "/foo"
        >>> NginxRegexRewrittenProvider.parse_location_path("/(foo/bar)/(.*)|/(foo/bar)")
        "/foo/bar"
        """
        # 兼容解析旧正则表达式
        if path_pattern.endswith("()(.*)"):
            return remove_suffix(path_pattern, "()(.*)")
        elif path_pattern.endswith("(/|$)(.*)"):
            return remove_suffix(path_pattern, "(/|$)(.*)") + "/"

        if "|" not in path_pattern:
            # 处理规则 "/(foo)/(.*)()"
            # 去掉末尾的 /(.*)(), 再去掉 "/(" 和 ")" 即可提取出 path_str
            return "/" + remove_suffix(path_pattern, "/(.*)()")[2:-1] + "/"
        # 处理规则 "/(foo)/(.*)|/(foo)"
        # 从子字符串 "/(.*)|" 截断, 再去掉 "/(" 和 ")" 即可提取出 path_str
        return "/" + path_pattern[: path_pattern.index("/(.*)|")][2:-1]


class ConfigurationSnippetPatcher:
    START_MARK = "# WARNING: BLOCK FOR IngressNginxAdaptor BEGIN"
    END_MARK = "# WARNING: BLOCK FOR IngressNginxAdaptor END"
    REGEX = f"{START_MARK}.+?{END_MARK}"

    @dataclass
    class PatchResult:
        """
        :param changed: whether the given configuration_snippet is changed by ConfigurationSnippetPatcher
        :param configuration_snippet: the new(or unchanged if changed is False) configuration_snippet
        """

        changed: bool
        configuration_snippet: str

    def patch(self, base: str, extend: str) -> PatchResult:
        """patch base configuration_snippet with extend if unpatched

        :return: PatchResult
        """
        if not re.findall(self.REGEX, base, re.M | re.S):
            return self.PatchResult(True, "\n".join([base, self.START_MARK, extend, self.END_MARK]))
        return self.PatchResult(False, base)

    def unpatch(self, snippet: str) -> PatchResult:
        """reverse patch_configuration_snippet

        :return: PatchResult
        """
        if re.findall(self.REGEX, snippet, re.M | re.S):
            return self.PatchResult(True, re.sub(self.REGEX, "", snippet, count=0, flags=re.M | re.S).strip())
        return self.PatchResult(False, snippet)

    def parse_service_info_from_rules(self, rules: List[ResourceInstance]) -> Tuple[str, str]:
        """parse Tuple[service_name, service_port_name] from List[IngressRule]

        :raise ValueError: if not ingress backend can be found or different backends found
        """
        svc_info_pairs = set()
        for rule in rules:
            if not rule.get("http"):
                continue
            for ingress_path in rule.http.paths:
                if not ingress_path.backend.get("service"):
                    continue
                service_name = ingress_path.backend.service.name
                service_port_name = ingress_path.backend.service.port.name
                if not service_port_name:
                    raise ValueError(f"Only support ingress with port name, detail: {ingress_path.backend}")
                svc_info_pairs.add((service_name, service_port_name))

        if not svc_info_pairs:
            raise ValueError("No ingress backend can be found in ingress rules")
        elif len(svc_info_pairs) != 1:
            raise ValueError(f"different backends found: {svc_info_pairs}")
        return svc_info_pairs.pop()
