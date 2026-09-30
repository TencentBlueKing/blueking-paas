// Package oci 定义代理对 OCI Distribution v2 请求的路由解析、拒绝原因与错误响应格式。
package oci

import (
	"net/http"
	"net/url"
	"regexp"
	"strings"
)

// 路由类型，写入审计日志 route 字段
const (
	RoutePing     = "ping"
	RouteManifest = "manifest"
	RouteBlob     = "blob"
	RouteUpload   = "upload"
	RouteTags     = "tags"
	RouteUnknown  = "unknown"
)

// Action 是请求所需的动作，空值表示路由不支持该方法
type Action string

const (
	ActionPull Action = "pull"
	ActionPush Action = "push"
)

// OCI Distribution Spec 的仓库名、tag 与 digest 规则
var (
	repoNameRE = regexp.MustCompile(`^[a-z0-9]+(?:(?:\.|_|__|-+)[a-z0-9]+)*(?:/[a-z0-9]+(?:(?:\.|_|__|-+)[a-z0-9]+)*)*$`)
	tagRE      = regexp.MustCompile(`^[a-zA-Z0-9_][a-zA-Z0-9._-]{0,127}$`)
	digestRE   = regexp.MustCompile(`^[a-z0-9]+(?:[.+_-][a-z0-9]+)*:[a-zA-Z0-9=_-]+$`)
)

type routeRule struct {
	re      *regexp.Regexp
	kind    string
	session bool
	methods map[string]Action // 方法 -> 所需动作
}

var rules = []routeRule{
	{regexp.MustCompile(`^(.+)/manifests/([^/]+)$`), RouteManifest, false, map[string]Action{"GET": ActionPull, "HEAD": ActionPull, "PUT": ActionPush}},
	{regexp.MustCompile(`^(.+)/blobs/uploads/?$`), RouteUpload, false, map[string]Action{"POST": ActionPush}},
	{regexp.MustCompile(`^(.+)/blobs/uploads/([^/]+)$`), RouteUpload, true, map[string]Action{"GET": ActionPush, "PATCH": ActionPush, "PUT": ActionPush}},
	{regexp.MustCompile(`^(.+)/blobs/([^/]+)$`), RouteBlob, false, map[string]Action{"GET": ActionPull, "HEAD": ActionPull}},
	{regexp.MustCompile(`^(.+)/tags/list$`), RouteTags, false, map[string]Action{"GET": ActionPull}},
}

// Route 是一次请求的解析结果，仓库路径均为客户端视角：<上游别名>/<上游仓库路径>
type Route struct {
	Kind string
	// Repo 为客户端视角的仓库路径，Kind 为 ping 或 unknown 时为空
	Repo string
	// Upstream 为 Repo 的第一段，即上游别名
	Upstream string
	// Reference 为 manifest 的 tag 或 digest、blob 的 digest、完成上传时的 digest 参数；不含上传会话标识
	Reference string
	// Action 为请求所需的动作，路由不支持该方法时为空
	Action Action
	// Session 表示请求针对已有的上传会话
	Session bool
	// SessionID 为客户端回传的上传会话标识（代理签名的 token），只用于会话校验，不写入审计
	SessionID string
	// MountFrom 为跨仓库挂载的来源仓库（客户端视角），非挂载请求为空
	MountFrom string
}

// Valid 表示路由已知、方法受支持，且仓库名（至少包含别名与一段仓库路径）与引用均合法
func (r Route) Valid() bool {
	if r.Kind == RoutePing {
		return r.Action != ""
	}
	if r.Kind == RouteUnknown || r.Action == "" || !repoNameRE.MatchString(r.Repo) || !strings.Contains(r.Repo, "/") {
		return false
	}
	switch r.Kind {
	case RouteManifest:
		return tagRE.MatchString(r.Reference) || digestRE.MatchString(r.Reference)
	case RouteBlob:
		return digestRE.MatchString(r.Reference)
	case RouteUpload:
		return r.MountFrom == "" || repoNameRE.MatchString(r.MountFrom)
	default:
		return true
	}
}

// IsPing 判断路径是否为 /v2/ 探活
func IsPing(path string) bool { return path == "/v2/" || path == "/v2" }

// ParseRoute 解析请求路由，不做任何授权判定。path 为未解码的路径（url.URL.EscapedPath），
// 合法的仓库名与引用不需要转义，含 % 的路径（如编码后的 / 或 \）一律视为未知路由。
func ParseRoute(method, path string, query url.Values) Route {
	if strings.Contains(path, "%") {
		return Route{Kind: RouteUnknown}
	}
	if IsPing(path) {
		r := Route{Kind: RoutePing}
		if method == http.MethodGet || method == http.MethodHead {
			r.Action = ActionPull
		}
		return r
	}
	r := Route{Kind: RouteUnknown}
	rest, ok := strings.CutPrefix(path, "/v2/")
	if !ok {
		return r
	}
	for _, rule := range rules {
		m := rule.re.FindStringSubmatch(rest)
		if m == nil {
			continue
		}
		r.Kind, r.Repo, r.Session, r.Action = rule.kind, m[1], rule.session, rule.methods[method]
		switch {
		case rule.session:
			r.SessionID = m[2]
		case len(m) > 2:
			r.Reference = m[2]
		}
		break
	}
	r.Upstream, _, _ = strings.Cut(r.Repo, "/")
	if r.Kind == RouteUpload {
		switch {
		case r.Session && method == http.MethodPut:
			r.Reference = query.Get("digest")
		case !r.Session && method == http.MethodPost:
			r.MountFrom = query.Get("from")
		}
	}
	return r
}

// UpstreamOf 返回客户端视角仓库路径的上游别名
func UpstreamOf(repo string) string {
	alias, _, _ := strings.Cut(repo, "/")
	return alias
}
