package proxy

import (
	"maps"
	"net/http"
	"net/url"
	"strings"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/oci"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/upstream"
)

// aliasMapping 在客户端视角与上游视角之间转换仓库路径。客户端视角的仓库以 <别名>/ 开头，上游视角没有别名段。
type aliasMapping struct {
	alias string
}

// owns 判断客户端视角的仓库是否属于该上游
func (m aliasMapping) owns(repo string) bool { return oci.UpstreamOf(repo) == m.alias }

// upstreamRepo 把客户端视角的仓库 <别名>/<仓库> 转为上游视角的 <仓库>
func (m aliasMapping) upstreamRepo(repo string) string { return strings.TrimPrefix(repo, m.alias+"/") }

// upstreamPath 把客户端请求路径 /v2/<别名>/... 转为上游路径 /v2/...
func (m aliasMapping) upstreamPath(path string) string {
	return "/v2/" + strings.TrimPrefix(path, "/v2/"+m.alias+"/")
}

// clientPath 把上游路径 /v2/... 转为客户端路径 /v2/<别名>/...
func (m aliasMapping) clientPath(path string) string {
	return "/v2/" + m.alias + "/" + strings.TrimPrefix(path, "/v2/")
}

// forwardPlan 是请求通过全部客户端侧校验后的转发指令，生成后不再修改。
// 转发阶段只按它与上游通信，失败时返回 502。
type forwardPlan struct {
	upstream *upstream.Upstream
	alias    aliasMapping
	// route 为 mount 降级后的路由，审计与续传会话的签发都以它为准
	route oci.Route
	// target 为上游地址：普通请求去掉别名段，续传请求取自签名会话
	target *url.URL
	// scopes 为换取上游 Authorization 的 scope，上游返回 401 时据此作废缓存
	scopes []upstream.Scope
	// sessionExpiry 为续传会话的过期时刻，续传返回的新会话沿用它；非续传请求为 0
	sessionExpiry int64
}

// resolve 完成转发前的客户端侧校验与协议转换，生成转发计划。失败时返回的拒绝原因均对应 403。
func (s *Server) resolve(r *http.Request, rt oci.Route, query url.Values, d Decision) (*forwardPlan, oci.DenyReason) {
	// 1. 按路径第一段的别名查找上游：未配置的上游永不转发，上游主机也只取自配置，客户端无法指定
	up, ok := s.upstreams[rt.Upstream]
	if !ok {
		return nil, oci.DenyUnknownUpstream
	}
	alias := aliasMapping{alias: up.Alias}

	// 2. 开始上传请求中的 mount：跨上游、缺少 from 或来源不可读时降级为普通上传，之后的路由与查询参数都以降级结果为准
	rt, query = resolveMount(rt, query, d.DropMount, alias)

	// 3. 计算上游地址：主机始终是配置中的上游根地址，只决定路径与查询串
	target := *up.URL
	var expiry int64
	if rt.Session {
		// 续传请求：路径中的会话 token 是代理签发的，先验签并确认会话属于本仓库，
		// 再用会话中记录的上游续传地址（路径与查询串）替换，客户端无法改写上游地址或把会话挪到其他仓库
		sess, err := s.sessions.verify(rt.SessionID, rt.Repo)
		if err != nil {
			return nil, oci.DenyUploadSession
		}
		loc, err := url.Parse(sess.Location)
		if err != nil {
			return nil, oci.DenyUploadSession
		}
		target.Path, target.RawPath, target.RawQuery = loc.Path, loc.RawPath, loc.RawQuery
		// 客户端只需要提供完成上传时的 digest，其余参数（如 _state）以上游返回的为准
		if digest := query.Get("digest"); digest != "" {
			q := target.Query()
			q.Set("digest", digest)
			target.RawQuery = q.Encode()
		}
		// 续传返回的新会话沿用原会话的过期时刻，上传会话的总时长不会因续传而延长
		expiry = sess.Expiry
	} else {
		// 普通请求：去掉路径中的别名段即为上游路径；查询参数为 mount 降级后的结果，重新编码后转发
		target.Path = alias.upstreamPath(r.URL.Path)
		target.RawQuery = query.Encode()
	}

	return &forwardPlan{
		upstream:      up,
		alias:         alias,
		route:         rt,
		target:        &target,
		scopes:        upstreamScopes(rt, alias),
		sessionExpiry: expiry,
	}, ""
}

// resolveMount 处理开始上传请求中的 mount / from，返回降级后的路由与转发给上游的查询参数，不修改入参。
//
// 客户端把所有上游视为同一个 registry，会尝试跨上游挂载；直接转发会让上游按同名路径查找来源仓库。
// 缺少 from 的 mount 在部分 registry 上表示「从凭证可读的任意仓库挂载」，而代理的上游账号可读全平台。
// 以上情况以及来源不可读（dropMount）时，都去掉 mount / from，降级为普通上传；保留的 mount 去掉 from 中的别名段。
func resolveMount(rt oci.Route, query url.Values, dropMount bool, alias aliasMapping) (oci.Route, url.Values) {
	if rt.Kind != oci.RouteUpload || rt.Session || !query.Has("mount") && !query.Has("from") {
		return rt, query
	}
	query = maps.Clone(query)
	if rt.MountFrom == "" || !query.Has("mount") || dropMount || !alias.owns(rt.MountFrom) {
		query.Del("mount")
		query.Del("from")
		rt.MountFrom = ""
		// 降级后没有写入 mount 指定的 blob
		rt.Reference = query.Get("digest")
		return rt, query
	}
	query.Set("from", alias.upstreamRepo(rt.MountFrom))
	return rt, query
}

// upstreamScopes 按路由计算换取上游 Authorization 的 scope，仓库为上游视角。
// 上游 token 的权限范围只由授权结果决定，不采用上游质询中的 scope。
func upstreamScopes(rt oci.Route, alias aliasMapping) []upstream.Scope {
	// 上游 token 的 scope 是协议里的字符串，与路由动作类型分开
	actions := []string{string(oci.ActionPull)}
	if rt.Action == oci.ActionPush {
		actions = append(actions, string(oci.ActionPush))
	}
	scopes := []upstream.Scope{{Repo: alias.upstreamRepo(rt.Repo), Actions: actions}}
	if rt.MountFrom != "" {
		scopes = append(scopes, upstream.Scope{Repo: alias.upstreamRepo(rt.MountFrom), Actions: []string{string(oci.ActionPull)}})
	}
	return scopes
}
