package proxy_test

import (
	"bytes"
	"context"
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/authz"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/buildtoken"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/oci"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/proxy"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/upstream"
)

const testAudience = "bkpaas-registry-proxy:test"

// syncBuffer 收集审计输出
type syncBuffer struct {
	mu  sync.Mutex
	buf bytes.Buffer
}

func (b *syncBuffer) Write(p []byte) (int, error) {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.buf.Write(p)
}

func (b *syncBuffer) entries(t *testing.T) []proxy.AuditEntry {
	t.Helper()
	b.mu.Lock()
	defer b.mu.Unlock()
	var out []proxy.AuditEntry
	for _, line := range strings.Split(strings.TrimSpace(b.buf.String()), "\n") {
		if line == "" {
			continue
		}
		var e proxy.AuditEntry
		if err := json.Unmarshal([]byte(line), &e); err != nil {
			t.Fatalf("audit line %q: %v", line, err)
		}
		out = append(out, e)
	}
	return out
}

func (b *syncBuffer) String() string {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.buf.String()
}

// testEnv 是两个上游（A、B）与共享上传会话密钥的两个代理副本
type testEnv struct {
	regA, regB     *fakeRegistry
	aliasA, aliasB string
	proxy1, proxy2 *httptest.Server
	audit          *syncBuffer
	priv           ed25519.PrivateKey
	kid            string
}

func newTestEnv(t *testing.T) *testEnv {
	t.Helper()
	return newTestEnvWith(t, func(ups map[string]*upstream.Upstream) proxy.Authorizer {
		return &authz.PolicyAuthorizer{Upstreams: upstream.Aliases(ups)}
	})
}

func newTestEnvWith(t *testing.T, newAuthorizer func(map[string]*upstream.Upstream) proxy.Authorizer) *testEnv {
	t.Helper()
	e := &testEnv{regA: newFakeRegistry(t), regB: newFakeRegistry(t), audit: &syncBuffer{}}
	e.aliasA, _ = upstream.AliasOf(e.regA.host())
	e.aliasB, _ = upstream.AliasOf(e.regB.host())

	pub, priv, _ := ed25519.GenerateKey(rand.Reader)
	e.priv = priv
	e.kid = buildtoken.JWKThumbprint(base64.RawURLEncoding.EncodeToString(pub))
	keys := buildtoken.KeySet{e.kid: pub}
	uploadKey := bytes.Repeat([]byte("k"), 32)

	newProxy := func() *httptest.Server {
		var specs []upstream.Spec
		creds := map[string]upstream.Credential{}
		for alias, reg := range map[string]*fakeRegistry{e.aliasA: e.regA, e.aliasB: e.regB} {
			u, _ := url.Parse(reg.URL)
			specs = append(specs, upstream.Spec{Alias: alias, URL: u})
			creds[u.Host] = upstream.Credential{Username: fakeCredUser, Password: fakeCredPass}
		}
		ups, err := upstream.FromSpecs(specs, creds, upstream.Options{TokenMaxTTL: time.Minute})
		if err != nil {
			t.Fatal(err)
		}
		srv, err := proxy.New(proxy.Options{
			Upstreams:        ups,
			Authenticator:    &authz.TokenAuthenticator{Keys: keys, Audience: testAudience},
			Authorizer:       newAuthorizer(ups),
			Auditor:          proxy.NewJSONAuditor(e.audit),
			UploadSessionKey: uploadKey,
		})
		if err != nil {
			t.Fatal(err)
		}
		ts := httptest.NewServer(srv)
		t.Cleanup(ts.Close)
		return ts
	}
	e.proxy1, e.proxy2 = newProxy(), newProxy()
	return e
}

// token 签发一个构建 token：可推送 A/bkpaas/app:v1 与 A/bkpaas/app/cache:*，可拉取 A/ 与 B/，拒绝 A/bkpaas/
func (e *testEnv) token(t *testing.T, mutate ...func(jwt.MapClaims)) string {
	t.Helper()
	now := time.Now()
	c := jwt.MapClaims{
		"iss": buildtoken.Issuer, "aud": testAudience, "sub": "build-1", "jti": "jti-1",
		"iat": now.Unix(), "exp": now.Add(20 * time.Minute).Unix(), "ver": 1,
		"app_code": "demo", "module": "default",
		"push": []map[string]any{
			{"repo": e.aliasA + "/bkpaas/app", "tags": []string{"v1"}},
			{"repo": e.aliasA + "/bkpaas/app/cache", "tags": []string{"*"}},
		},
		"pull":      []string{e.aliasA + "/", e.aliasB + "/"},
		"pull_deny": []string{e.aliasA + "/bkpaas/"},
	}
	for _, m := range mutate {
		m(c)
	}
	tok := jwt.NewWithClaims(jwt.SigningMethodEdDSA, c)
	tok.Header["kid"] = e.kid
	s, err := tok.SignedString(e.priv)
	if err != nil {
		t.Fatal(err)
	}
	return s
}

type reqOpt func(*http.Request)

func withHeader(k, v string) reqOpt { return func(r *http.Request) { r.Header.Set(k, v) } }

func do(t *testing.T, method, rawURL, token string, body []byte, opts ...reqOpt) (*http.Response, []byte) {
	t.Helper()
	var rd io.Reader
	if body != nil {
		rd = bytes.NewReader(body)
	}
	req, err := http.NewRequest(method, rawURL, rd)
	if err != nil {
		t.Fatal(err)
	}
	if token != "" {
		req.SetBasicAuth("bkpaas-build", token)
	}
	for _, o := range opts {
		o(req)
	}
	client := &http.Client{CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
	resp, err := client.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = resp.Body.Close() }()
	b, _ := io.ReadAll(resp.Body)
	return resp, b
}

func withQuery(loc, key, value string) string {
	u, _ := url.Parse(loc)
	q := u.Query()
	q.Set(key, value)
	u.RawQuery = q.Encode()
	return u.String()
}

func assertProxyError(t *testing.T, resp *http.Response, body []byte, status int, deny string) {
	t.Helper()
	if resp.StatusCode != status {
		t.Fatalf("status = %d, want %d, body = %s", resp.StatusCode, status, body)
	}
	want := `"bkpaas-registry-proxy: ` + deny + `"`
	if !strings.Contains(string(body), want) {
		t.Fatalf("body = %s, want message %s", body, want)
	}
	if resp.Header.Get("Content-Type") != "application/json" {
		t.Fatalf("content-type = %q", resp.Header.Get("Content-Type"))
	}
	wa := resp.Header.Get("WWW-Authenticate")
	if (status == http.StatusUnauthorized) != (wa == `Basic realm="bkpaas-registry-proxy"`) {
		t.Fatalf("status %d with WWW-Authenticate %q", status, wa)
	}
}

// assertNoLeak 检查响应中不含上游凭证、上游 token 与上游 token 服务地址
func assertNoLeak(t *testing.T, e *testEnv, resp *http.Response, body []byte) {
	t.Helper()
	var dump strings.Builder
	_ = resp.Header.Write(&dump)
	dump.Write(body)
	for _, needle := range []string{fakeCredPass, "/token", "upstream-session", "Bearer "} {
		if strings.Contains(dump.String(), needle) {
			t.Fatalf("response leaks %q:\n%s", needle, dump.String())
		}
	}
	for _, reg := range []*fakeRegistry{e.regA, e.regB} {
		reg.mu.Lock()
		for tok := range reg.tokens {
			if strings.Contains(dump.String(), tok) {
				reg.mu.Unlock()
				t.Fatalf("response leaks upstream token")
			}
		}
		reg.mu.Unlock()
	}
}

func TestPingChallenge(t *testing.T) {
	e := newTestEnv(t)
	resp, body := do(t, http.MethodGet, e.proxy1.URL+"/v2/", "", nil)
	assertProxyError(t, resp, body, http.StatusUnauthorized, "token_missing")

	resp, body = do(t, http.MethodGet, e.proxy1.URL+"/v2/", "forged", nil)
	assertProxyError(t, resp, body, http.StatusUnauthorized, "token_invalid")

	resp, body = do(t, http.MethodGet, e.proxy1.URL+"/v2/", e.token(t), nil)
	if resp.StatusCode != http.StatusOK || string(body) != "{}" || resp.Header.Get("Docker-Distribution-API-Version") != "registry/2.0" {
		t.Fatalf("authenticated ping: %d %s %v", resp.StatusCode, body, resp.Header)
	}
	// Bearer 方式同样接受
	resp, _ = do(t, http.MethodHead, e.proxy1.URL+"/v2/", "", nil, withHeader("Authorization", "Bearer "+e.token(t)))
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("bearer ping: %d", resp.StatusCode)
	}

	entries := e.audit.entries(t)
	if entries[0].Route != "ping" || entries[0].Status != 401 || entries[0].Deny != "" {
		t.Fatalf("tokenless ping audit = %+v", entries[0])
	}
	if entries[1].Deny != "token_invalid" {
		t.Fatalf("forged ping audit = %+v", entries[1])
	}
	if len(e.regA.recorded()) != 0 {
		t.Fatal("ping must not reach upstream")
	}
}

func TestPullManifestStripsUpstreamChallenge(t *testing.T) {
	e := newTestEnv(t)
	e.regA.putManifest("python/python", "3", []byte(`{"schemaVersion":2}`))

	resp, body := do(t, http.MethodGet, e.proxy1.URL+"/v2/"+e.aliasA+"/python/python/manifests/3", e.token(t), nil,
		withHeader("Cookie", "client=1"))
	if resp.StatusCode != http.StatusOK || string(body) != `{"schemaVersion":2}` {
		t.Fatalf("pull manifest: %d %s", resp.StatusCode, body)
	}
	for _, h := range []string{"WWW-Authenticate", "Set-Cookie", "Keep-Alive", "X-Hop"} {
		if resp.Header.Get(h) != "" {
			t.Fatalf("upstream header %s leaked: %v", h, resp.Header)
		}
	}
	assertNoLeak(t, e, resp, body)

	reqs := e.regA.recorded()
	last := reqs[len(reqs)-1]
	if last.Path != "/v2/python/python/manifests/3" {
		t.Fatalf("upstream path = %q, alias must be stripped", last.Path)
	}
	if !strings.HasPrefix(last.Authorization, "Bearer ") || strings.Contains(last.Authorization, e.token(t)[:20]) {
		t.Fatalf("upstream Authorization = %q, must be the proxy's upstream token", last.Authorization)
	}
	if last.Cookie != "" {
		t.Fatal("client cookie must not reach upstream")
	}

	entries := e.audit.entries(t)
	got := entries[len(entries)-1]
	if got.Sub != "build-1" || got.JTI != "jti-1" || got.Route != "manifest" || got.Repo != e.aliasA+"/python/python" ||
		got.Upstream != e.aliasA || got.Reference != "3" || got.Status != 200 || got.RespBytes != int64(len(body)) || got.RemoteAddr != "127.0.0.1" {
		t.Fatalf("audit = %+v", got)
	}
	if strings.Contains(e.audit.String(), e.token(t)[:40]) || strings.Contains(e.audit.String(), fakeCredPass) {
		t.Fatal("audit log contains credentials")
	}
}

// HTTP/2 禁止连接相关的头，上游的逐跳头透传会让严格的客户端（curl）判定为协议错误
func TestHTTP2ClientWithHopHeaders(t *testing.T) {
	e := newTestEnv(t)
	e.regA.putManifest("python/python", "3", []byte(`{}`))
	h2 := httptest.NewUnstartedServer(e.proxy1.Config.Handler)
	h2.EnableHTTP2 = true
	h2.StartTLS()
	defer h2.Close()

	req, _ := http.NewRequest(http.MethodGet, h2.URL+"/v2/"+e.aliasA+"/python/python/manifests/3", nil)
	req.SetBasicAuth("bkpaas-build", e.token(t))
	resp, err := h2.Client().Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.ProtoMajor != 2 || resp.StatusCode != http.StatusOK {
		t.Fatalf("proto=%s status=%d", resp.Proto, resp.StatusCode)
	}
	for _, h := range []string{"Connection", "Keep-Alive", "X-Hop"} {
		if resp.Header.Get(h) != "" {
			t.Fatalf("hop-by-hop header %s forwarded over HTTP/2", h)
		}
	}
}

// blob 下载：上游返回 307 时原样交给客户端，直接返回数据时由代理流式转发
func TestBlobRedirectPassThroughAndStreaming(t *testing.T) {
	e := newTestEnv(t)
	content := bytes.Repeat([]byte("layer"), 100000)
	d := e.regA.putBlob("python/python", content)
	e.regB.putBlob("python/python", content)
	e.regA.setRedirectBlobs(true)

	resp, body := do(t, http.MethodGet, e.proxy1.URL+"/v2/"+e.aliasA+"/python/python/blobs/"+d, e.token(t), nil)
	if resp.StatusCode != http.StatusTemporaryRedirect || !strings.HasPrefix(resp.Header.Get("Location"), e.regA.storage.URL+"/bucket/") {
		t.Fatalf("harbor-like blob: %d Location=%q", resp.StatusCode, resp.Header.Get("Location"))
	}
	assertNoLeak(t, e, resp, body)

	resp, body = do(t, http.MethodGet, e.proxy1.URL+"/v2/"+e.aliasB+"/python/python/blobs/"+d, e.token(t), nil)
	if resp.StatusCode != http.StatusOK || !bytes.Equal(body, content) {
		t.Fatalf("direct blob: %d len=%d", resp.StatusCode, len(body))
	}

	entries := e.audit.entries(t)
	storageHost, _ := url.Parse(e.regA.storage.URL)
	if entries[0].RedirectHost != storageHost.Hostname() || entries[0].Reference != d {
		t.Fatalf("redirect audit = %+v", entries[0])
	}
	if entries[1].RespBytes != int64(len(content)) {
		t.Fatalf("streaming audit = %+v", entries[1])
	}
}

// 分块上传与 Location 改写：同一上传会话的请求分别落到两个副本
func TestChunkedUploadAcrossReplicas(t *testing.T) {
	e := newTestEnv(t)
	tok := e.token(t)
	repo := "/v2/" + e.aliasA + "/bkpaas/app"
	chunk1, chunk2 := bytes.Repeat([]byte("a"), 1000), bytes.Repeat([]byte("b"), 500)
	d := digestOf(append(append([]byte(nil), chunk1...), chunk2...))

	resp, _ := do(t, http.MethodPost, e.proxy1.URL+repo+"/blobs/uploads/", tok, nil)
	loc := resp.Header.Get("Location")
	if resp.StatusCode != http.StatusAccepted || !strings.HasPrefix(loc, repo+"/blobs/uploads/") {
		t.Fatalf("start upload: %d Location=%q", resp.StatusCode, loc)
	}
	if strings.Contains(loc, "upstream-") || strings.Contains(loc, "_state") {
		t.Fatalf("upstream upload state leaked in Location %q", loc)
	}

	resp, _ = do(t, http.MethodPatch, e.proxy2.URL+loc, tok, chunk1)
	if resp.StatusCode != http.StatusAccepted {
		t.Fatalf("patch on replica 2: %d", resp.StatusCode)
	}
	loc = resp.Header.Get("Location")
	resp, _ = do(t, http.MethodPatch, e.proxy1.URL+loc, tok, chunk2)
	if resp.StatusCode != http.StatusAccepted {
		t.Fatalf("patch on replica 1: %d", resp.StatusCode)
	}
	loc = resp.Header.Get("Location")
	resp, _ = do(t, http.MethodPut, e.proxy2.URL+withQuery(loc, "digest", d), tok, nil)
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("commit on replica 2: %d", resp.StatusCode)
	}
	if got := resp.Header.Get("Location"); got != repo+"/blobs/"+d {
		t.Fatalf("commit Location = %q", got)
	}

	// kaniko 推送前的权限预检会 DELETE 上传会话，代理拒绝
	resp, body := do(t, http.MethodDelete, e.proxy1.URL+loc, tok, nil)
	assertProxyError(t, resp, body, http.StatusForbidden, "delete_not_allowed")

	for _, entry := range e.audit.entries(t) {
		if entry.Route == "upload" && strings.Contains(entry.Reference, ".") {
			t.Fatalf("audit leaks upload session: %+v", entry)
		}
	}
}

func TestUploadSessionForgery(t *testing.T) {
	e := newTestEnv(t)
	tok := e.token(t)
	repo := "/v2/" + e.aliasA + "/bkpaas/app"

	resp, body := do(t, http.MethodPatch, e.proxy1.URL+repo+"/blobs/uploads/forged.session", tok, []byte("x"))
	assertProxyError(t, resp, body, http.StatusForbidden, "invalid_upload_session")

	// 会话绑定仓库，不能拿到其他可推送仓库使用
	resp, _ = do(t, http.MethodPost, e.proxy1.URL+repo+"/blobs/uploads/", tok, nil)
	session := strings.TrimPrefix(resp.Header.Get("Location"), repo+"/blobs/uploads/")
	session, _, _ = strings.Cut(session, "?")
	resp, body = do(t, http.MethodPatch, e.proxy1.URL+"/v2/"+e.aliasA+"/bkpaas/app/cache/blobs/uploads/"+session, tok, []byte("x"))
	assertProxyError(t, resp, body, http.StatusForbidden, "invalid_upload_session")
}

// 跨上游 mount 降级为普通上传
func TestCrossUpstreamMountDowngrade(t *testing.T) {
	e := newTestEnv(t)
	tok := e.token(t)
	d := e.regB.putBlob("python/python", []byte("base-layer"))
	e.regA.putBlob("python/python", []byte("base-layer"))
	e.regA.putBlob("bkpaas/other", []byte("base-layer"))
	target := e.proxy1.URL + "/v2/" + e.aliasA + "/bkpaas/app/blobs/uploads/"

	// 来源在上游 B：降级为普通上传，上游 A 收不到指向 B 路径的 mount
	resp, _ := do(t, http.MethodPost, target+"?mount="+d+"&from="+e.aliasB+"/python/python", tok, nil)
	if resp.StatusCode != http.StatusAccepted {
		t.Fatalf("cross-upstream mount: %d", resp.StatusCode)
	}
	// 来源命中 pull_deny：同样降级
	resp, _ = do(t, http.MethodPost, target+"?mount="+d+"&from="+e.aliasA+"/bkpaas/other", tok, nil)
	if resp.StatusCode != http.StatusAccepted {
		t.Fatalf("pull-denied mount: %d", resp.StatusCode)
	}
	for _, r := range e.regA.recorded() {
		if strings.Contains(r.Query, "mount") || strings.Contains(r.Query, "from") {
			t.Fatalf("upstream A received mount request: %+v", r)
		}
	}

	// 同上游且来源可读：转发 mount，from 去掉别名
	resp, _ = do(t, http.MethodPost, target+"?mount="+d+"&from="+e.aliasA+"/python/python", tok, nil)
	if resp.StatusCode != http.StatusCreated || resp.Header.Get("Location") != "/v2/"+e.aliasA+"/bkpaas/app/blobs/"+d {
		t.Fatalf("same-upstream mount: %d Location=%q", resp.StatusCode, resp.Header.Get("Location"))
	}
	reqs := e.regA.recorded()
	q, _ := url.ParseQuery(reqs[len(reqs)-1].Query)
	if q.Get("from") != "python/python" {
		t.Fatalf("upstream mount from = %q", q.Get("from"))
	}
}

// 上游作废 token 后，下一次请求重新鉴权
func TestUpstreamTokenRevokedRetry(t *testing.T) {
	e := newTestEnv(t)
	tok := e.token(t)
	e.regA.putManifest("python/python", "3", []byte(`{}`))
	path := e.proxy1.URL + "/v2/" + e.aliasA + "/python/python/manifests/3"

	if resp, _ := do(t, http.MethodGet, path, tok, nil); resp.StatusCode != http.StatusOK {
		t.Fatalf("first pull: %d", resp.StatusCode)
	}
	if resp, _ := do(t, http.MethodHead, path, tok, nil); resp.StatusCode != http.StatusOK || e.regA.tokenRequests() != 1 {
		t.Fatalf("cached pull: %d, token requests %d", resp.StatusCode, e.regA.tokenRequests())
	}
	e.regA.revokeTokens()
	resp, body := do(t, http.MethodGet, path, tok, nil)
	if resp.StatusCode != http.StatusOK || string(body) != `{}` {
		t.Fatalf("pull after revoke: %d %s", resp.StatusCode, body)
	}
	if n := e.regA.tokenRequests(); n != 2 {
		t.Fatalf("token requests = %d, want 2", n)
	}

	// 有请求体的请求不重试，返回 502；缓存已作废，下一次请求重新鉴权
	put := e.proxy1.URL + "/v2/" + e.aliasA + "/bkpaas/app/manifests/v1"
	if resp, _ := do(t, http.MethodPut, put, tok, []byte(`{"a":1}`)); resp.StatusCode != http.StatusCreated {
		t.Fatalf("first put: %d", resp.StatusCode)
	}
	e.regA.revokeTokens()
	resp, body = do(t, http.MethodPut, put, tok, []byte(`{"a":1}`))
	assertProxyError(t, resp, body, http.StatusBadGateway, "upstream_auth_failed")
	assertNoLeak(t, e, resp, body)
	if resp, _ := do(t, http.MethodPut, put, tok, []byte(`{"a":1}`)); resp.StatusCode != http.StatusCreated {
		t.Fatalf("put after re-auth: %d", resp.StatusCode)
	}
}

func TestUpstreamFailures(t *testing.T) {
	e := newTestEnv(t)
	tok := e.token(t)

	// 上游拒绝代理凭证，且错误体中带有敏感信息
	e.regA.setIntercept(func(w http.ResponseWriter, r *http.Request) bool {
		if r.URL.Path != "/token" {
			return false
		}
		http.Error(w, "invalid credential for robot:"+fakeCredPass, http.StatusUnauthorized)
		return true
	})
	resp, body := do(t, http.MethodGet, e.proxy1.URL+"/v2/"+e.aliasA+"/python/python/manifests/3", tok, nil)
	assertProxyError(t, resp, body, http.StatusBadGateway, "upstream_auth_failed")
	assertNoLeak(t, e, resp, body)

	// 上游不可达
	e.regB.Close()
	resp, body = do(t, http.MethodGet, e.proxy1.URL+"/v2/"+e.aliasB+"/python/python/manifests/3", tok, nil)
	assertProxyError(t, resp, body, http.StatusBadGateway, "upstream_unreachable")
	resp, _ = do(t, http.MethodHead, e.proxy1.URL+"/v2/"+e.aliasB+"/python/python/manifests/3", tok, nil)
	if resp.StatusCode != http.StatusBadGateway {
		t.Fatalf("HEAD unreachable: %d", resp.StatusCode)
	}
}

func TestRejectedRequestsDoNotReachUpstream(t *testing.T) {
	e := newTestEnv(t)
	tok := e.token(t)
	expired := e.token(t, func(c jwt.MapClaims) {
		c["exp"] = time.Now().Add(-time.Hour).Unix()
		c["iat"] = time.Now().Add(-2 * time.Hour).Unix()
	})
	a := e.proxy1.URL + "/v2/" + e.aliasA

	cases := []struct {
		name, method, url, token string
		status                   int
		deny                     string
	}{
		{"no token", http.MethodGet, a + "/python/python/manifests/3", "", 401, "token_missing"},
		{"expired", http.MethodGet, a + "/python/python/manifests/3", expired, 401, "token_expired"},
		{"unknown upstream", http.MethodGet, e.proxy1.URL + "/v2/docker-io/library/python/manifests/3", tok, 403, "unknown_upstream"},
		{"delete manifest", http.MethodDelete, a + "/bkpaas/app/manifests/v1", tok, 403, "delete_not_allowed"},
		{"tag not granted", http.MethodPut, a + "/bkpaas/app/manifests/latest", tok, 403, "tag_not_granted"},
		{"push not granted", http.MethodPost, a + "/bkpaas/other/blobs/uploads/", tok, 403, "push_not_granted"},
		{"pull denied", http.MethodGet, a + "/bkpaas/other/manifests/v1", tok, 403, "pull_denied"},
		{"catalog", http.MethodGet, e.proxy1.URL + "/v2/_catalog", tok, 404, "route_not_found"},
		{"non v2", http.MethodGet, e.proxy1.URL + "/api/v2.0/projects", tok, 404, "route_not_found"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp, body := do(t, tc.method, tc.url, tc.token, nil)
			assertProxyError(t, resp, body, tc.status, tc.deny)
		})
	}
	if n := len(e.regA.recorded()); n != 0 {
		t.Fatalf("upstream received %d requests", n)
	}
	for _, entry := range e.audit.entries(t) {
		if entry.Deny == "" {
			t.Fatalf("rejected request audited without deny: %+v", entry)
		}
	}
}

func TestPathAndReferenceValidation(t *testing.T) {
	e := newTestEnv(t)
	tok := e.token(t)
	a := e.proxy1.URL + "/v2/" + e.aliasA
	for _, p := range []string{
		"/python/python/manifests/..",
		"/python/python/manifests/%2e%2e",
		"/python%2Fpython/manifests/3",
		"/python/python/blobs/latest",
		"/python/python/blobs/sha256:..",
	} {
		t.Run(p, func(t *testing.T) {
			resp, body := do(t, http.MethodGet, a+p, tok, nil)
			assertProxyError(t, resp, body, http.StatusNotFound, "route_not_found")
		})
	}
	if n := len(e.regA.recorded()); n != 0 {
		t.Fatalf("upstream received %d requests", n)
	}
}

// 缺少 from 的 mount 在部分 registry 上表示从凭证可读的任意仓库挂载，必须降级
func TestMountWithoutFromDowngraded(t *testing.T) {
	e := newTestEnv(t)
	d := e.regA.putBlob("python/python", []byte("base"))
	resp, _ := do(t, http.MethodPost, e.proxy1.URL+"/v2/"+e.aliasA+"/bkpaas/app/blobs/uploads/?mount="+d, e.token(t), nil)
	if resp.StatusCode != http.StatusAccepted {
		t.Fatalf("status = %d", resp.StatusCode)
	}
	for _, r := range e.regA.recorded() {
		if strings.Contains(r.Query, "mount") {
			t.Fatalf("upstream received mount without from: %+v", r)
		}
	}
}

func TestUploadLocationOnForeignHostRejected(t *testing.T) {
	e := newTestEnv(t)
	e.regA.setIntercept(func(w http.ResponseWriter, r *http.Request) bool {
		if r.Method != http.MethodPost || !strings.HasSuffix(r.URL.Path, "/blobs/uploads/") {
			return false
		}
		w.Header().Set("Location", "https://storage.example.com/v2/bkpaas/app/blobs/uploads/u1")
		w.WriteHeader(http.StatusAccepted)
		return true
	})
	resp, body := do(t, http.MethodPost, e.proxy1.URL+"/v2/"+e.aliasA+"/bkpaas/app/blobs/uploads/", e.token(t), nil)
	assertProxyError(t, resp, body, http.StatusBadGateway, "upstream_unreachable")
	if strings.Contains(resp.Header.Get("Location"), "storage.example.com") {
		t.Fatal("foreign upload location leaked")
	}
}

func TestOnlyAllowedHeadersForwarded(t *testing.T) {
	e := newTestEnv(t)
	e.regA.putManifest("python/python", "3", []byte(`{}`))
	resp, _ := do(t, http.MethodGet, e.proxy1.URL+"/v2/"+e.aliasA+"/python/python/manifests/3", e.token(t), nil,
		withHeader("Accept", "application/vnd.oci.image.manifest.v1+json"),
		withHeader("User-Agent", "kaniko/v1.24.0"),
		withHeader("X-Forwarded-For", "10.0.0.1"),
		withHeader("X-Custom", "1"))
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("status = %d", resp.StatusCode)
	}
	reqs := e.regA.recorded()
	h := reqs[len(reqs)-1].Header
	if h.Get("Accept") != "application/vnd.oci.image.manifest.v1+json" || h.Get("User-Agent") != "kaniko/v1.24.0" {
		t.Fatalf("allowed headers not forwarded: %v", h)
	}
	if h.Get("X-Forwarded-For") != "" || h.Get("X-Custom") != "" {
		t.Fatalf("unexpected headers forwarded: %v", h)
	}
}

func TestHeadBlobKeepsContentLength(t *testing.T) {
	e := newTestEnv(t)
	content := bytes.Repeat([]byte("z"), 12345)
	d := e.regB.putBlob("python/python", content)
	resp, body := do(t, http.MethodHead, e.proxy1.URL+"/v2/"+e.aliasB+"/python/python/blobs/"+d, e.token(t), nil)
	if resp.StatusCode != http.StatusOK || resp.ContentLength != int64(len(content)) || len(body) != 0 {
		t.Fatalf("HEAD blob: status=%d length=%d body=%d", resp.StatusCode, resp.ContentLength, len(body))
	}
	if resp.Header.Get("Docker-Content-Digest") != d {
		t.Fatalf("digest header = %q", resp.Header.Get("Docker-Content-Digest"))
	}
}

type allowAll struct{}

func (allowAll) Authorize(proxy.Principal, string, oci.Route) proxy.Decision { return proxy.Decision{} }

// 授权钩子放行一切时，DELETE、未配置的上游与跨上游 mount 仍然不会到达上游
func TestDefenseInDepthWithPermissiveAuthorizer(t *testing.T) {
	e := newTestEnvWith(t, func(map[string]*upstream.Upstream) proxy.Authorizer { return allowAll{} })
	tok := e.token(t)
	a := e.proxy1.URL + "/v2/" + e.aliasA

	for _, u := range []string{a + "/bkpaas/app/manifests/v1", a + "/bkpaas/app/blobs/sha256:x"} {
		resp, body := do(t, http.MethodDelete, u, tok, nil)
		assertProxyError(t, resp, body, http.StatusForbidden, "delete_not_allowed")
	}
	resp, body := do(t, http.MethodGet, e.proxy1.URL+"/v2/docker-io/library/python/manifests/3", tok, nil)
	assertProxyError(t, resp, body, http.StatusForbidden, "unknown_upstream")
	resp, body = do(t, http.MethodGet, e.proxy1.URL+"/v2/_catalog", tok, nil)
	assertProxyError(t, resp, body, http.StatusNotFound, "route_not_found")
	if n := len(e.regA.recorded()); n != 0 {
		t.Fatalf("upstream received %d requests", n)
	}

	d := e.regB.putBlob("python/python", []byte("x"))
	resp, _ = do(t, http.MethodPost, a+"/bkpaas/app/blobs/uploads/?mount="+d+"&from="+e.aliasB+"/python/python", tok, nil)
	if resp.StatusCode != http.StatusAccepted {
		t.Fatalf("cross-upstream mount: %d", resp.StatusCode)
	}
	for _, r := range e.regA.recorded() {
		if strings.Contains(r.Query, "from") {
			t.Fatalf("upstream A received mount request: %+v", r)
		}
	}
}

func TestHeadErrorHasNoBody(t *testing.T) {
	e := newTestEnv(t)
	resp, body := do(t, http.MethodHead, e.proxy1.URL+"/v2/"+e.aliasA+"/bkpaas/other/manifests/v1", e.token(t), nil)
	if resp.StatusCode != http.StatusForbidden || len(body) != 0 {
		t.Fatalf("HEAD: %d body=%q", resp.StatusCode, body)
	}
}

func TestTagsListLinkRewritten(t *testing.T) {
	e := newTestEnv(t)
	resp, _ := do(t, http.MethodGet, e.proxy1.URL+"/v2/"+e.aliasA+"/python/python/tags/list", e.token(t), nil)
	want := `</v2/` + e.aliasA + `/python/python/tags/list?last=v1&n=1>; rel="next"`
	if resp.StatusCode != http.StatusOK || resp.Header.Get("Link") != want {
		t.Fatalf("tags list: %d Link=%q", resp.StatusCode, resp.Header.Get("Link"))
	}
}

// 客户端中途断开时，发往上游的请求随之取消，不残留连接
func TestClientDisconnectCancelsUpstream(t *testing.T) {
	e := newTestEnv(t)
	cancelled := make(chan struct{})
	e.regB.setIntercept(func(w http.ResponseWriter, r *http.Request) bool {
		if !strings.Contains(r.URL.Path, "/blobs/") {
			return false
		}
		w.Header().Set("Content-Length", "1000000000")
		w.WriteHeader(http.StatusOK)
		buf := make([]byte, 32<<10)
		for {
			if _, err := w.Write(buf); err != nil {
				close(cancelled)
				return true
			}
		}
	})

	ctx, cancel := context.WithCancel(context.Background())
	req, _ := http.NewRequestWithContext(ctx, http.MethodGet, e.proxy1.URL+"/v2/"+e.aliasB+"/python/python/blobs/sha256:x", nil)
	req.SetBasicAuth("bkpaas-build", e.token(t))
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	_, _ = io.CopyN(io.Discard, resp.Body, 1<<20)
	cancel()
	_ = resp.Body.Close()

	select {
	case <-cancelled:
	case <-time.After(10 * time.Second):
		t.Fatal("upstream transfer was not cancelled after client disconnect")
	}
}
