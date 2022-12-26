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


class NginxPatternAdaptor:
    """Maintains compatibility for ingress-nginx >= 0.22.0, which use pattern in rewrite-target

    In Version 0.22.0 +, any substrings within the request URI that need to be passed to the rewritten path
    must explicitly be defined in a capture group.
    Ref: https://kubernetes.github.io/ingress-nginx/examples/rewrite/#rewrite-target
    """

    @staticmethod
    def make_configuration_snippet() -> str:
        """Make configuration snippet which set X-Script-Name as the sub-path provided from platform or custom domain

        Must use "configuration-snippet" instead of "server-snippet" otherwise "proxy-set-header"
        directive will stop working because it already can be found in location block.
        """
        # "/$1$3" is the sub-path provided from platform or custom domain, for root path case, it should be "/"
        # See also: the guarantee of make_location_path
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
            return "/({})/(.*)()".format(remove_suffix(trim_path, "/"))
        # adapter the trimPath that ends without slash
        return "/({})/(.*)|/({}$)".format(trim_path, trim_path)

    @staticmethod
    def parse_location_path(path_pattern: str) -> str:
        """parse path_str from path pattern(which is return by make_location_path)

        >>> NginxPatternAdaptor.parse_location_path("/()(.*)")
        "/"
        >>> NginxPatternAdaptor.parse_location_path("/(foo)/(.*)()")
        "/foo/"
        >>> NginxPatternAdaptor.parse_location_path("/(foo/bar)/(.*)()")
        "/foo/bar/
        >>> NginxPatternAdaptor.parse_location_path("/(foo)/(.*)|/(foo)")
        "/foo"
        >>> NginxPatternAdaptor.parse_location_path("/(foo/bar)/(.*)|/(foo/bar)")
        "/foo/bar"
        """
        # 兼容解析旧正则表达式
        if "()(.*)" in path_pattern:
            return path_pattern[: -len("()(.*)")]
        elif "(/|$)(.*)" in path_pattern:
            return path_pattern[: -len("(/|$)(.*)")] + "/"

        if "|" not in path_pattern:
            # 处理规则 "/(foo)/(.*)()"
            # 去掉末尾的 /(.*)(), 再去掉 "/(" 和 ")" 即可提取出 path_str
            return "/" + remove_suffix(path_pattern, "/(.*)()")[2:-1] + "/"
        # 处理规则 "/(foo)/(.*)|/(foo)"
        # 从子字符串 "/(.*)|" 截断, 再去掉 "/(" 和 ")" 即可提取出 path_str
        return "/" + path_pattern[: path_pattern.index("/(.*)|")][2:-1]
