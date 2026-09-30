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
	"time"
)

const (
	// 上游未返回 expires_in 时按 Docker token 规范取 60 秒
	defaultTokenExpiresIn = 60 * time.Second
	challengeTTL          = 10 * time.Minute
	maxTokenResponseBytes = 1 << 20
)

// 上游鉴权失败的归类，取值与拒绝原因一致
const (
	ReasonAuthFailed  = "upstream_auth_failed"
	ReasonUnreachable = "upstream_unreachable"
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
	Reason string
	Err    error
}

func (e *AuthError) Error() string { return e.Reason + ": " + e.Err.Error() }
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

// Authorization 返回访问上游所需的 Authorization 头，按 scope 缓存，过期前复用。
// 返回空串表示匿名访问。hit 表示命中缓存。
func (u *Upstream) Authorization(ctx context.Context, scopes []Scope) (header string, hit bool, err error) {
	if u.cred != nil && u.cred.RegistryToken != "" {
		return "Bearer " + u.cred.RegistryToken, true, nil
	}
	key := ScopeKey(scopes)
	if h, ok := u.cached(key); ok {
		return h, true, nil
	}
	// 同一 scope 的并发未命中只换一次 token；不继承调用方的取消，避免一个客户端断开导致其他请求一起失败
	v, err, _ := u.flight.Do(key, func() (any, error) {
		if h, ok := u.cached(key); ok {
			return h, nil
		}
		fctx, cancel := context.WithTimeout(context.WithoutCancel(ctx), u.authTimeout)
		defer cancel()
		h, ttl, err := u.fetch(fctx, scopes)
		if err != nil {
			return "", err
		}
		u.mu.Lock()
		u.cache[key] = cachedAuth{header: h, expires: u.now().Add(ttl)}
		u.mu.Unlock()
		return h, nil
	})
	if err != nil {
		return "", false, err
	}
	return v.(string), false, nil
}

// Invalidate 作废 scope 对应的缓存，并清除缓存的质询，下次重新走完整的鉴权流程
func (u *Upstream) Invalidate(scopes []Scope) {
	key := ScopeKey(scopes)
	u.mu.Lock()
	delete(u.cache, key)
	u.challenge = nil
	u.mu.Unlock()
}

func (u *Upstream) cached(key string) (string, bool) {
	u.mu.Lock()
	defer u.mu.Unlock()
	c, ok := u.cache[key]
	if !ok {
		return "", false
	}
	if !u.now().Before(c.expires) {
		delete(u.cache, key)
		return "", false
	}
	return c.header, true
}

func (u *Upstream) fetch(ctx context.Context, scopes []Scope) (string, time.Duration, error) {
	ch, err := u.getChallenge(ctx)
	if err != nil {
		return "", 0, err
	}
	switch strings.ToLower(ch.scheme) {
	case "":
		// /v2/ 无需认证：有凭证时仍带上 Basic，兼容只对部分仓库要求认证的上游
		if u.cred == nil {
			return "", u.maxTTL, nil
		}
		return u.basic(), u.maxTTL, nil
	case "basic":
		if u.cred == nil {
			return "", 0, authFailed("upstream %s requires credentials but none configured", u.URL.Host)
		}
		return u.basic(), u.maxTTL, nil
	case "bearer":
		token, ttl, err := u.requestToken(ctx, ch.params, scopes)
		if err != nil {
			u.mu.Lock()
			u.challenge = nil
			u.mu.Unlock()
			return "", 0, err
		}
		return "Bearer " + token, ttl, nil
	default:
		return "", 0, authFailed("upstream %s: unsupported auth scheme %q", u.URL.Host, ch.scheme)
	}
}

func (u *Upstream) basic() string {
	return "Basic " + base64.StdEncoding.EncodeToString([]byte(u.cred.Username+":"+u.cred.Password))
}

// getChallenge 请求上游 /v2/ 获取认证方式，结果缓存一段时间
func (u *Upstream) getChallenge(ctx context.Context) (*cachedChallenge, error) {
	u.mu.Lock()
	if c := u.challenge; c != nil && u.now().Before(c.expires) {
		u.mu.Unlock()
		return c, nil
	}
	u.mu.Unlock()

	ping := *u.URL
	ping.Path = "/v2/"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, ping.String(), nil)
	if err != nil {
		return nil, authFailed("build challenge request: %v", err)
	}
	resp, err := u.authClient.Do(req)
	if err != nil {
		return nil, &AuthError{Reason: ReasonUnreachable, Err: err}
	}
	defer drain(resp.Body)

	c := &cachedChallenge{expires: u.now().Add(challengeTTL)}
	switch resp.StatusCode {
	case http.StatusOK:
	case http.StatusUnauthorized:
		header := resp.Header.Get("WWW-Authenticate")
		if header == "" {
			return nil, authFailed("upstream %s: 401 without WWW-Authenticate", u.URL.Host)
		}
		c.scheme, c.params = parseChallenge(header)
	default:
		return nil, authFailed("upstream %s: challenge status %d", u.URL.Host, resp.StatusCode)
	}
	u.mu.Lock()
	u.challenge = c
	u.mu.Unlock()
	return c, nil
}

// requestToken 按 Docker Registry token 规范换取 Bearer token。scope 由代理计算，忽略质询中的 scope。
func (u *Upstream) requestToken(ctx context.Context, params map[string]string, scopes []Scope) (string, time.Duration, error) {
	realm, err := url.Parse(params["realm"])
	if err != nil || realm.Host == "" || (realm.Scheme != "https" && realm.Scheme != "http") {
		return "", 0, authFailed("upstream %s: invalid token realm", u.URL.Host)
	}
	// 上游为 HTTPS 时，不把凭证发给明文的 token 服务
	if u.URL.Scheme == "https" && realm.Scheme != "https" {
		return "", 0, authFailed("upstream %s: refuse plaintext token realm %s", u.URL.Host, realm.Host)
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
	if u.cred != nil {
		req.SetBasicAuth(u.cred.Username, u.cred.Password)
	}
	resp, err := u.authClient.Do(req)
	if err != nil {
		return "", 0, &AuthError{Reason: ReasonUnreachable, Err: err}
	}
	defer drain(resp.Body)
	if resp.StatusCode != http.StatusOK {
		return "", 0, authFailed("upstream %s: token endpoint %s status %d", u.URL.Host, realm.Host, resp.StatusCode)
	}
	var body struct {
		Token       string `json:"token"`
		AccessToken string `json:"access_token"`
		ExpiresIn   int64  `json:"expires_in"`
	}
	if err := json.NewDecoder(io.LimitReader(resp.Body, maxTokenResponseBytes)).Decode(&body); err != nil {
		return "", 0, authFailed("upstream %s: invalid token response", u.URL.Host)
	}
	token := body.Token
	if token == "" {
		token = body.AccessToken
	}
	if token == "" {
		return "", 0, authFailed("upstream %s: token response missing token", u.URL.Host)
	}
	return token, u.tokenTTL(time.Duration(body.ExpiresIn) * time.Second), nil
}

// tokenTTL 在上游有效期的 90% 处过期，并以 maxTTL 为上限
func (u *Upstream) tokenTTL(expiresIn time.Duration) time.Duration {
	if expiresIn <= 0 {
		expiresIn = defaultTokenExpiresIn
	}
	ttl := expiresIn * 9 / 10
	if u.maxTTL > 0 && ttl > u.maxTTL {
		ttl = u.maxTTL
	}
	return max(ttl, time.Second)
}

func authFailed(format string, args ...any) error {
	return &AuthError{Reason: ReasonAuthFailed, Err: fmt.Errorf(format, args...)}
}

// ReasonOf 返回错误对应的拒绝原因，未归类的错误视为上游不可达
func ReasonOf(err error) string {
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
