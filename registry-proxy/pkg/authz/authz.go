// Package authz 把构建 token 校验（buildtoken）与授权判定（policy）接入代理的鉴权、授权钩子。
package authz

import (
	"net/http"
	"strings"
	"time"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/buildtoken"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/oci"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/policy"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/proxy"
)

// TokenAuthenticator 校验请求携带的构建 token
type TokenAuthenticator struct {
	Keys     buildtoken.KeySet
	Audience string
	Now      func() time.Time
}

type principal struct {
	claims *buildtoken.Claims
}

func (p principal) Identity() proxy.Identity {
	return proxy.Identity{
		Subject: p.claims.Subject,
		TokenID: p.claims.ID,
		AppCode: p.claims.AppCode,
		Module:  p.claims.Module,
	}
}

func (a *TokenAuthenticator) Authenticate(r *http.Request) (proxy.Principal, string) {
	now := time.Now
	if a.Now != nil {
		now = a.Now
	}
	c, deny, _ := buildtoken.Verify(TokenFromRequest(r), a.Keys, a.Audience, now())
	if deny != "" {
		return nil, deny
	}
	return principal{claims: c}, ""
}

// TokenFromRequest 读取构建 token：Basic 认证的密码段（忽略用户名），或 Bearer token
func TokenFromRequest(r *http.Request) string {
	scheme, rest, _ := strings.Cut(strings.TrimSpace(r.Header.Get("Authorization")), " ")
	switch strings.ToLower(scheme) {
	case "bearer":
		return strings.TrimSpace(rest)
	case "basic":
		if _, password, ok := r.BasicAuth(); ok {
			return password
		}
	}
	return ""
}

// PolicyAuthorizer 按授权规则判定，Upstreams 为代理配置的上游别名集合
type PolicyAuthorizer struct {
	Upstreams map[string]bool
}

func (a *PolicyAuthorizer) Authorize(p proxy.Principal, method string, rt oci.Route) proxy.Decision {
	pr, ok := p.(principal)
	if !ok {
		return proxy.Decision{Status: http.StatusUnauthorized, Deny: oci.DenyTokenInvalid}
	}
	d := policy.Decide(pr.claims, a.Upstreams, method, rt)
	return proxy.Decision{Status: d.Status, Deny: d.Deny, DropMount: d.DropMount}
}
