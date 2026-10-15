package upstream

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"sort"
	"strings"
	"sync"
	"time"

	"golang.org/x/sync/singleflight"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/oci"
)

const (
	// 上游未返回 expires_in 时按 Docker token 规范取 60 秒
	defaultTokenExpiresIn = 60 * time.Second
	challengeTTL          = 10 * time.Minute
	maxTokenResponseBytes = 1 << 20
	// 每个上游按 scope 缓存的 token 条数上限。token 有效期不超过 TokenMaxTTL，
	// 正常构建在该时间窗内用到的 scope 远少于此；前缀授权下可以用随机仓库名刷出大量 scope
	maxCachedAuths = 16384
)

// 上游鉴权失败的归类，取值就是对应的拒绝原因
const (
	ReasonAuthFailed  = oci.DenyUpstreamAuth
	ReasonUnreachable = oci.DenyUpstreamUnreached
)

// Scope 是代理为一次请求计算的上游仓库权限。代理只使用自己计算的 scope，
// 不采用上游质询中的 scope：上游 token 的权限范围只由授权结果决定。
// 部分上游返回的 scope 是与仓库无关的固定值。
type Scope struct {
	// Repo 为上游仓库路径（不含别名）
	Repo    string
	Actions []string
}

func (s Scope) String() string {
	return "repository:" + s.Repo + ":" + strings.Join(s.Actions, ",")
}

// AuthError 是换取上游 Authorization 失败，Reason 为 ReasonAuthFailed 或 ReasonUnreachable。
// Error() 只含状态码与主机等排障信息，不含凭证与上游响应体。
type AuthError struct {
	Reason oci.DenyReason
	Err    error
}

func (e *AuthError) Error() string { return string(e.Reason) + ": " + e.Err.Error() }
func (e *AuthError) Unwrap() error { return e.Err }

type cachedAuth struct {
	header  string
	expires time.Time
}

type cachedChallenge struct {
	scheme  string
	params  map[string]string
	expires time.Time
}

// ScopeKey 返回 scope 集合的缓存键，与 scope 的顺序无关
func ScopeKey(scopes []Scope) string {
	parts := make([]string, 0, len(scopes))
	for _, s := range scopes {
		actions := append([]string(nil), s.Actions...)
		sort.Strings(actions)
		parts = append(parts, Scope{Repo: s.Repo, Actions: actions}.String())
	}
	sort.Strings(parts)
	return strings.Join(parts, " ")
}

// AuthProvider 用代理自身的上游凭证（一级凭证）换取并缓存访问某个上游所需的 Authorization，只在转发前使用。
// 换取过程会请求上游的 /v2/ 质询与 token 服务，但不转发客户端请求。
type AuthProvider struct {
	// base 为上游根地址，质询请求发往它的 /v2/
	base *url.URL
	// cred 为代理自身的上游凭证，启动时从配置读取，查不到为 nil 即匿名访问。运行期间只读，更新凭证需重启
	cred *Credential
	// client 与转发共用上游的 Transport，timeout 限制一次换取（质询 + 换 token）的总时长
	client  *http.Client
	timeout time.Duration
	maxTTL  time.Duration
	now     func() time.Time

	// 以下缓存启动时为空，由 Header 在未命中时用 cred 现换现存；只在内存中，重启后重新换取。
	// 条目在查找时发现过期即清除，上游返回 401 时由 Invalidate 作废
	mu sync.Mutex
	// byScope 按 scope 缓存 Bearer token（以 ScopeKey 为键），条目数不超过 maxCached
	byScope   map[string]cachedAuth
	maxCached int
	// unscoped 缓存与 scope 无关、所有 scope 共用的 Authorization：上游 /v2/ 无需认证或要求 Basic 时使用。
	// 未过期时不查 byScope
	unscoped *cachedAuth
	// challenge 缓存上游 /v2/ 返回的认证方式，有效期 challengeTTL
	challenge *cachedChallenge
	flight    singleflight.Group
}

// HasCredential 返回代理是否持有该上游的凭证
func (p *AuthProvider) HasCredential() bool { return p.cred != nil }

// Header 返回访问上游所需的 Authorization 头，按 scope 缓存，过期前复用。
// 返回空串表示匿名访问。hit 表示命中缓存。
func (p *AuthProvider) Header(ctx context.Context, scopes []Scope) (header string, hit bool, err error) {
	key := ScopeKey(scopes)
	if h, ok := p.cached(key); ok {
		return h, true, nil
	}
	// 同一 scope 的并发未命中只换一次 token；不继承调用方的取消，避免一个客户端断开导致其他请求一起失败
	v, err, _ := p.flight.Do(key, func() (any, error) {
		if h, ok := p.cached(key); ok {
			return h, nil
		}
		fctx, cancel := context.WithTimeout(context.WithoutCancel(ctx), p.timeout)
		defer cancel()
		h, ttl, scoped, err := p.exchangeAuthorization(fctx, scopes)
		if err != nil {
			return "", err
		}
		p.store(key, cachedAuth{header: h, expires: p.now().Add(ttl)}, scoped)
		return h, nil
	})
	if err != nil {
		return "", false, err
	}
	return v.(string), false, nil
}

// Invalidate 作废 scope 对应的缓存，并清除缓存的质询，下次重新走完整的鉴权流程
func (p *AuthProvider) Invalidate(scopes []Scope) {
	key := ScopeKey(scopes)
	p.mu.Lock()
	delete(p.byScope, key)
	p.unscoped = nil
	p.challenge = nil
	p.mu.Unlock()
}

// cached 查找缓存：先查与 scope 无关的 unscoped，再查 byScope
func (p *AuthProvider) cached(key string) (string, bool) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if c := p.unscoped; c != nil {
		if p.now().Before(c.expires) {
			return c.header, true
		}
		p.unscoped = nil
	}
	c, ok := p.byScope[key]
	if !ok {
		return "", false
	}
	if !p.now().Before(c.expires) {
		delete(p.byScope, key)
		return "", false
	}
	return c.header, true
}

// store 写入缓存：与 scope 无关的结果写入 unscoped，否则按 scope 写入 byScope。
// byScope 已满时先清除过期条目，仍然满则不缓存，只影响后续请求是否需要重新换 token
func (p *AuthProvider) store(key string, c cachedAuth, scoped bool) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if !scoped {
		p.unscoped = &c
		return
	}
	if len(p.byScope) >= p.maxCached {
		now := p.now()
		for k, v := range p.byScope {
			if !now.Before(v.expires) {
				delete(p.byScope, k)
			}
		}
		if len(p.byScope) >= p.maxCached {
			return
		}
	}
	p.byScope[key] = c
}

// exchangeAuthorization 用代理凭证向上游换取 Authorization，不查也不写缓存：
// 先按上游 /v2/ 的质询确定认证方式（质询有缓存），Bearer 时再向 token 服务换 token。
// scoped 表示结果与 scope 相关（Bearer），否则所有 scope 共用（匿名或 Basic）
func (p *AuthProvider) exchangeAuthorization(ctx context.Context, scopes []Scope) (header string, ttl time.Duration, scoped bool, err error) {
	ch, err := p.getChallenge(ctx)
	if err != nil {
		return "", 0, false, err
	}
	switch strings.ToLower(ch.scheme) {
	case "":
		// /v2/ 无需认证：有凭证时仍带上 Basic，兼容只对部分仓库要求认证的上游
		if p.cred == nil {
			return "", p.maxTTL, false, nil
		}
		return p.basic(), p.maxTTL, false, nil
	case "basic":
		if p.cred == nil {
			return "", 0, false, authFailed("upstream %s requires credentials but none configured", p.base.Host)
		}
		return p.basic(), p.maxTTL, false, nil
	case "bearer":
		token, ttl, err := p.requestToken(ctx, ch.params, scopes)
		if err != nil {
			p.mu.Lock()
			p.challenge = nil
			p.mu.Unlock()
			return "", 0, false, err
		}
		return "Bearer " + token, ttl, true, nil
	default:
		return "", 0, false, authFailed("upstream %s: unsupported auth scheme %q", p.base.Host, ch.scheme)
	}
}

func (p *AuthProvider) basic() string {
	return "Basic " + base64.StdEncoding.EncodeToString([]byte(p.cred.Username+":"+p.cred.Password))
}

// getChallenge 请求上游 /v2/ 获取认证方式，结果缓存一段时间
func (p *AuthProvider) getChallenge(ctx context.Context) (*cachedChallenge, error) {
	p.mu.Lock()
	if c := p.challenge; c != nil && p.now().Before(c.expires) {
		p.mu.Unlock()
		return c, nil
	}
	p.mu.Unlock()

	ping := *p.base
	ping.Path = "/v2/"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, ping.String(), nil)
	if err != nil {
		return nil, authFailed("build challenge request: %v", err)
	}
	resp, err := p.client.Do(req)
	if err != nil {
		return nil, &AuthError{Reason: ReasonUnreachable, Err: err}
	}
	defer drain(resp.Body)

	c := &cachedChallenge{expires: p.now().Add(challengeTTL)}
	switch resp.StatusCode {
	case http.StatusOK:
	case http.StatusUnauthorized:
		header := resp.Header.Get("WWW-Authenticate")
		if header == "" {
			return nil, authFailed("upstream %s: 401 without WWW-Authenticate", p.base.Host)
		}
		c.scheme, c.params = parseChallenge(header)
	default:
		return nil, authFailed("upstream %s: challenge status %d", p.base.Host, resp.StatusCode)
	}
	p.mu.Lock()
	p.challenge = c
	p.mu.Unlock()
	return c, nil
}

// requestToken 按 Docker Registry token 规范换取 Bearer token。scope 由代理计算，忽略质询中的 scope。
func (p *AuthProvider) requestToken(ctx context.Context, params map[string]string, scopes []Scope) (string, time.Duration, error) {
	// 按照 oci distribution 规范，不校验 realm 和 registry 是否属于同一主机。只有当上游本身已被入侵时这里才可能有问题
	realm, err := url.Parse(params["realm"])
	if err != nil || realm.Host == "" || (realm.Scheme != "https" && realm.Scheme != "http") {
		return "", 0, authFailed("upstream %s: invalid token realm", p.base.Host)
	}
	// 上游为 HTTPS 时，不把凭证发给明文的 token 服务
	if p.base.Scheme == "https" && realm.Scheme != "https" {
		return "", 0, authFailed("upstream %s: refuse plaintext token realm %s", p.base.Host, realm.Host)
	}
	q := realm.Query()
	if service := params["service"]; service != "" {
		q.Set("service", service)
	}
	for _, s := range scopes {
		q.Add("scope", s.String())
	}
	realm.RawQuery = q.Encode()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, realm.String(), nil)
	if err != nil {
		return "", 0, authFailed("build token request: %v", err)
	}
	if p.cred != nil {
		req.SetBasicAuth(p.cred.Username, p.cred.Password)
	}
	resp, err := p.client.Do(req)
	if err != nil {
		return "", 0, &AuthError{Reason: ReasonUnreachable, Err: err}
	}
	defer drain(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return "", 0, authFailed("upstream %s: token endpoint %s status %d", p.base.Host, realm.Host, resp.StatusCode)
	}
	var body struct {
		Token       string `json:"token"`
		AccessToken string `json:"access_token"`
		ExpiresIn   int64  `json:"expires_in"`
	}
	if err := json.NewDecoder(io.LimitReader(resp.Body, maxTokenResponseBytes)).Decode(&body); err != nil {
		return "", 0, authFailed("upstream %s: invalid token response", p.base.Host)
	}
	token := body.Token
	if token == "" {
		token = body.AccessToken
	}
	if token == "" {
		return "", 0, authFailed("upstream %s: token response missing token", p.base.Host)
	}
	return token, p.tokenTTL(time.Duration(body.ExpiresIn) * time.Second), nil
}

// tokenTTL 在上游有效期的 90% 处过期，并以 maxTTL 为上限
func (p *AuthProvider) tokenTTL(expiresIn time.Duration) time.Duration {
	if expiresIn <= 0 {
		expiresIn = defaultTokenExpiresIn
	}
	ttl := expiresIn * 9 / 10
	if p.maxTTL > 0 && ttl > p.maxTTL {
		ttl = p.maxTTL
	}
	return max(ttl, time.Second)
}

func authFailed(format string, args ...any) error {
	return &AuthError{Reason: ReasonAuthFailed, Err: fmt.Errorf(format, args...)}
}

// ReasonOf 返回错误对应的拒绝原因，未归类的错误视为上游不可达
func ReasonOf(err error) oci.DenyReason {
	var ae *AuthError
	if errors.As(err, &ae) {
		return ae.Reason
	}
	return ReasonUnreachable
}

func parseChallenge(header string) (string, map[string]string) {
	scheme, rest, _ := strings.Cut(strings.TrimSpace(header), " ")
	params := map[string]string{}
	for _, part := range splitParams(rest) {
		k, v, ok := strings.Cut(part, "=")
		if !ok {
			continue
		}
		params[strings.ToLower(strings.TrimSpace(k))] = strings.Trim(strings.TrimSpace(v), `"`)
	}
	return scheme, params
}

// splitParams 按逗号拆分质询参数，忽略引号内的逗号（scope 值里可能有逗号）
func splitParams(s string) []string {
	var parts []string
	start, quoted := 0, false
	for i, ch := range s {
		switch ch {
		case '"':
			quoted = !quoted
		case ',':
			if !quoted {
				parts = append(parts, s[start:i])
				start = i + 1
			}
		}
	}
	return append(parts, s[start:])
}

func drain(body io.ReadCloser) {
	_, _ = io.Copy(io.Discard, io.LimitReader(body, maxTokenResponseBytes))
	_ = body.Close()
}
