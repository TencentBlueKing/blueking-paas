from textwrap import dedent

from paas_wl.networking.ingress.constants import DomainsStructureType
from paas_wl.networking.ingress.entities.ingress import get_domains_struct_type
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

        struct_type = get_domains_struct_type(self.domains)
        if struct_type == DomainsStructureType.ALL_DIRECT_ACCESS:
            return self.format_direct_snippet()
        elif struct_type == DomainsStructureType.CUSTOMIZED_SUBPATH:
            # while an ingress object might has many paths, only one path can be used for making snippet annotation,
            # We will pick the shortest path when multiple were given.
            shortest_path = sorted(self.domains[0].path_prefix_list, key=len)[0]
            return self.format_subpath_snippet(shortest_path)
        else:
            raise RuntimeError('SubpathCompatPlugin do not support non-standard domains')

    @staticmethod
    def format_direct_snippet() -> str:
        snippets = [
            # Without this header, blueapps will not be able to set the correct path prefix
            'proxy_set_header X-Script-Name /;',
            # No need to add any other headers start with "X-Forwarded-*", because ingress-nginx will take care
            # of them, see ingress-nginx's config option: "use-forwarded-headers" for more infomations.
        ]
        return '\n'.join(snippets)

    @staticmethod
    def format_subpath_snippet(fallback: str) -> str:
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
        # To know "How the fallback work", see also: [nginx-variables-variable-scope](https://openresty.org/download/agentzh-nginx-tutorials-en.html#nginx-variables-variable-scope)  # noqa
        #
        # Notice: In nginx ingress-controller version 0.22.0 and beyond, rewrite target become are not backward
        # compatible with previous versions. Ingress rewritten path must be a regular expression that defined a
        # capture group.
        #
        # But at the same time, ingress-controller set the path which include a regular expression to $location_path.
        # So we have to rewrite the first section of $request_uri as $location_path, and pass it to upstream by header
        # X-Script-Name.
        snippet = dedent(
            f"""\
        set_by_lua_block $lua_x_script_name {{
            -- Get current requested URI with query string removed
            local uri = ngx.var.http_x_forwarded_uri or ngx.var.request_uri
            uri = ngx.re.gsub(uri, "\\\\?.*", "", "jo")

            -- Consider the first part of request path as script name, for example:
            -- request_uri: "/foo/bar?x=3" -> script_name: "/foo/"
            -- Doc for "ngx.re": https://github.com/openresty/lua-resty-core/blob/master/lib/ngx/re.md
            local ngx_re = require("ngx.re")
            local script_name = ngx_re.split(uri, '/')[2] or "{fallback}"
            return "/" .. script_name .. "/"
        }}
        proxy_set_header X-Script-Name $lua_x_script_name;
        """
        )
        return snippet
