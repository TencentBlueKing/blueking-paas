// Package policy 按固定顺序对已认证的请求做授权判定，默认拒绝。移植自参考实现 reference/policy.go。
package policy

import (
	"net/http"
	"strings"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/buildtoken"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/oci"
)

// Decision 是对单个已认证请求的判定。Status 为 0 表示放行并转发上游。
type Decision struct {
	Status int
	Deny   string
	// DropMount 为 true 时去掉 mount/from 参数，把跨仓库挂载降级为普通上传
	DropMount bool
}

// Decide 按固定的授权判定顺序处理一个已通过认证的请求，默认拒绝。
// upstreams 为代理配置中的上游别名集合。上传会话签名的校验不在此处，由会话层负责。
func Decide(c *buildtoken.Claims, upstreams map[string]bool, method string, rt oci.Route) Decision {
	if rt.Kind == oci.RoutePing {
		if rt.Action == "" {
			return Decision{Status: http.StatusNotFound, Deny: oci.DenyRouteNotFound}
		}
		return Decision{}
	}

	// 1. DELETE 一律拒绝；未知路由、非法仓库名、路由不支持的方法返回 404
	if method == http.MethodDelete {
		return Decision{Status: http.StatusForbidden, Deny: oci.DenyDeleteNotAllowed}
	}
	if !rt.Valid() {
		return Decision{Status: http.StatusNotFound, Deny: oci.DenyRouteNotFound}
	}
	// 2. 别名必须在代理配置中
	if !upstreams[rt.Upstream] {
		return Decision{Status: http.StatusForbidden, Deny: oci.DenyUnknownUpstream}
	}

	if rt.Action == oci.ActionPush {
		// 3. push 授权：仓库精确匹配；推送 manifest 时引用必须在 tags 内
		g := pushGrant(c, rt.Repo)
		if g == nil {
			return Decision{Status: http.StatusForbidden, Deny: oci.DenyPushNotGranted}
		}
		if rt.Kind == oci.RouteManifest && !allows(g, rt.Reference) {
			return Decision{Status: http.StatusForbidden, Deny: oci.DenyTagNotGranted}
		}
		if rt.MountFrom != "" {
			d := Decision{}
			d.DropMount = oci.UpstreamOf(rt.MountFrom) != rt.Upstream || PullDecision(c, rt.MountFrom) != ""
			return d
		}
		return Decision{}
	}

	// 4~7. pull：push 授权仓库 → pull_deny → pull → 其余拒绝
	if deny := PullDecision(c, rt.Repo); deny != "" {
		return Decision{Status: http.StatusForbidden, Deny: deny}
	}
	return Decision{}
}

// pushGrant 返回该仓库的推送授权。仓库名精确匹配，没有对应授权时返回 nil。
func pushGrant(c *buildtoken.Claims, repo string) *buildtoken.PushGrant {
	for i := range c.Push {
		if c.Push[i].Repo == repo {
			return &c.Push[i]
		}
	}
	return nil
}

// PullDecision 返回空串表示允许拉取，否则返回拒绝原因
func PullDecision(c *buildtoken.Claims, repo string) string {
	switch {
	case pushGrant(c, repo) != nil:
		return ""
	case matchAny(c.PullDeny, repo):
		return oci.DenyPullDenied
	case matchAny(c.Pull, repo):
		return ""
	default:
		return oci.DenyPullNotGranted
	}
}

// matchAny：以 / 结尾的条目为前缀匹配，否则精确匹配
func matchAny(patterns []string, repo string) bool {
	for _, p := range patterns {
		if strings.HasSuffix(p, "/") && strings.HasPrefix(repo, p) || p == repo {
			return true
		}
	}
	return false
}

// allows：tags 含 "*" 时允许任意 tag 与 digest；否则只允许列出的 tag
func allows(g *buildtoken.PushGrant, ref string) bool {
	for _, t := range g.Tags {
		if t == "*" || t == ref {
			return true
		}
	}
	return false
}
