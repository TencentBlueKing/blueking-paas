package proxy_test

import (
	"bytes"
	"context"
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/golang-jwt/jwt/v5"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

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

func (b *syncBuffer) String() string {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.buf.String()
}

func (b *syncBuffer) entries() []proxy.AuditEntry {
	var out []proxy.AuditEntry
	for _, line := range strings.Split(strings.TrimSpace(b.String()), "\n") {
		if line == "" {
			continue
		}
		var e proxy.AuditEntry
		Expect(json.Unmarshal([]byte(line), &e)).To(Succeed(), "audit line %q", line)
		out = append(out, e)
	}
	return out
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

// newTestEnv 创建测试环境，customize 用于覆盖代理的部分配置
func newTestEnv(customize ...func(*proxy.Options)) *testEnv {
	e := &testEnv{regA: newFakeRegistry(), regB: newFakeRegistry(), audit: &syncBuffer{}}
	e.aliasA, _ = upstream.AliasOf(e.regA.host())
	e.aliasB, _ = upstream.AliasOf(e.regB.host())

	pub, priv, _ := ed25519.GenerateKey(rand.Reader)
	e.priv = priv
	e.kid = buildtoken.JWKThumbprint(base64.RawURLEncoding.EncodeToString(pub))

	newProxy := func() *httptest.Server {
		var specs []upstream.Spec
		creds := map[string]upstream.Credential{}
		for alias, reg := range map[string]*fakeRegistry{e.aliasA: e.regA, e.aliasB: e.regB} {
			u, _ := url.Parse(reg.URL)
			specs = append(specs, upstream.Spec{Alias: alias, URL: u})
			creds[u.Host] = upstream.Credential{Username: fakeCredUser, Password: fakeCredPass}
		}
		ups, err := upstream.FromSpecs(specs, creds, upstream.Options{TokenMaxTTL: time.Minute})
		Expect(err).NotTo(HaveOccurred())
		opts := proxy.Options{
			Upstreams:        ups,
			Authenticator:    &authz.TokenAuthenticator{Keys: buildtoken.KeySet{e.kid: pub}, Audience: testAudience},
			Authorizer:       &authz.PolicyAuthorizer{Upstreams: upstream.Aliases(ups)},
			Auditor:          proxy.NewJSONAuditor(e.audit),
			UploadSessionKey: bytes.Repeat([]byte("k"), 32),
		}
		for _, c := range customize {
			c(&opts)
		}
		srv, err := proxy.New(opts)
		Expect(err).NotTo(HaveOccurred())
		ts := httptest.NewServer(srv)
		DeferCleanup(ts.Close)
		return ts
	}
	e.proxy1, e.proxy2 = newProxy(), newProxy()
	return e
}

// token 签发一个构建 token：可推送 A/bkpaas/app:v1 与 A/bkpaas/app/cache:*，可拉取 A/ 与 B/，拒绝 A/bkpaas/
func (e *testEnv) token(mutate ...func(jwt.MapClaims)) string {
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
	Expect(err).NotTo(HaveOccurred())
	return s
}

type reqOpt func(*http.Request)

func withHeader(k, v string) reqOpt { return func(r *http.Request) { r.Header.Set(k, v) } }

// do 发送请求并读完响应体，不跟随重定向
func do(method, rawURL, token string, body []byte, opts ...reqOpt) (*http.Response, []byte) {
	var rd io.Reader
	if body != nil {
		rd = bytes.NewReader(body)
	}
	req, err := http.NewRequest(method, rawURL, rd)
	Expect(err).NotTo(HaveOccurred())
	if token != "" {
		req.SetBasicAuth("bkpaas-build", token)
	}
	for _, o := range opts {
		o(req)
	}
	client := &http.Client{CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
	resp, err := client.Do(req)
	Expect(err).NotTo(HaveOccurred())
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

// assertProxyError 检查代理自身产生的 OCI 错误响应：状态码、拒绝原因标记，以及只有 401 带质询
func assertProxyError(resp *http.Response, body []byte, status int, deny string) {
	GinkgoHelper()
	Expect(resp.StatusCode).To(Equal(status), "body = %s", body)
	Expect(string(body)).To(ContainSubstring(`"bkpaas-registry-proxy: ` + deny + `"`))
	Expect(resp.Header.Get("Content-Type")).To(Equal("application/json"))
	if status == http.StatusUnauthorized {
		Expect(resp.Header.Get("WWW-Authenticate")).To(Equal(`Basic realm="bkpaas-registry-proxy"`))
	} else {
		Expect(resp.Header.Get("WWW-Authenticate")).To(BeEmpty())
	}
}

// assertNoLeak 检查响应中不含上游凭证、上游 token 与上游 token 服务地址
func assertNoLeak(e *testEnv, resp *http.Response, body []byte) {
	GinkgoHelper()
	var dump strings.Builder
	_ = resp.Header.Write(&dump)
	dump.Write(body)
	for _, needle := range []string{fakeCredPass, "/token", "upstream-session", "Bearer "} {
		Expect(dump.String()).NotTo(ContainSubstring(needle))
	}
	for _, reg := range []*fakeRegistry{e.regA, e.regB} {
		reg.mu.Lock()
		for tok := range reg.tokens {
			Expect(dump.String()).NotTo(ContainSubstring(tok), "response leaks upstream token")
		}
		reg.mu.Unlock()
	}
}

var _ = Describe("Server", func() {
	var e *testEnv
	// validToken 供表格用例延迟签发 token：Entry 在构建 spec 树时求值，e 在 BeforeEach 中才赋值
	validToken := func() string { return e.token() }

	BeforeEach(func() { e = newTestEnv() })

	Describe("/v2/ ping", func() {
		It("challenges without a valid token and never reaches upstream", func() {
			resp, body := do(http.MethodGet, e.proxy1.URL+"/v2/", "", nil)
			assertProxyError(resp, body, http.StatusUnauthorized, "token_missing")
			resp, body = do(http.MethodGet, e.proxy1.URL+"/v2/", "forged", nil)
			assertProxyError(resp, body, http.StatusUnauthorized, "token_invalid")

			resp, body = do(http.MethodGet, e.proxy1.URL+"/v2/", e.token(), nil)
			Expect(resp.StatusCode).To(Equal(http.StatusOK))
			Expect(string(body)).To(Equal("{}"))
			Expect(resp.Header.Get("Docker-Distribution-API-Version")).To(Equal("registry/2.0"))

			By("accepting Bearer as well")
			resp, _ = do(http.MethodHead, e.proxy1.URL+"/v2/", "", nil, withHeader("Authorization", "Bearer "+e.token()))
			Expect(resp.StatusCode).To(Equal(http.StatusOK))

			By("not auditing a tokenless ping as denied")
			entries := e.audit.entries()
			Expect(entries[0].Route).To(Equal("ping"))
			Expect(entries[0].Status).To(Equal(http.StatusUnauthorized))
			Expect(entries[0].Deny).To(BeEmpty())
			Expect(entries[1].Deny).To(Equal("token_invalid"))
			Expect(e.regA.recorded()).To(BeEmpty())
		})
	})

	Describe("pull", func() {
		BeforeEach(func() { e.regA.putManifest("python/python", "3", []byte(`{"schemaVersion":2}`)) })

		It("strips the alias, uses proxy credentials and strips upstream challenges", func() {
			resp, body := do(http.MethodGet, e.proxy1.URL+"/v2/"+e.aliasA+"/python/python/manifests/3", e.token(), nil,
				withHeader("Cookie", "client=1"))
			Expect(resp.StatusCode).To(Equal(http.StatusOK))
			Expect(string(body)).To(Equal(`{"schemaVersion":2}`))
			for _, h := range []string{"WWW-Authenticate", "Set-Cookie", "Keep-Alive", "X-Hop"} {
				Expect(resp.Header.Get(h)).To(BeEmpty(), "upstream header %s leaked", h)
			}
			assertNoLeak(e, resp, body)

			reqs := e.regA.recorded()
			last := reqs[len(reqs)-1]
			Expect(last.Path).To(Equal("/v2/python/python/manifests/3"), "alias must be stripped")
			Expect(last.Authorization).To(HavePrefix("Bearer "))
			Expect(last.Authorization).NotTo(ContainSubstring(e.token()[:20]), "must be the proxy's upstream token")
			Expect(last.Cookie).To(BeEmpty(), "client cookie must not reach upstream")

			By("auditing the request without credentials")
			entries := e.audit.entries()
			got := entries[len(entries)-1]
			Expect(got).To(Equal(proxy.AuditEntry{
				TS: got.TS, Ms: got.Ms,
				Sub: "build-1", JTI: "jti-1", AppCode: "demo", Module: "default", RemoteAddr: "127.0.0.1",
				Method: http.MethodGet, Route: "manifest", Repo: e.aliasA + "/python/python", Upstream: e.aliasA,
				Reference: "3", Status: http.StatusOK, RespBytes: int64(len(body)),
			}))
			Expect(e.audit.String()).NotTo(ContainSubstring(e.token()[:40]))
			Expect(e.audit.String()).NotTo(ContainSubstring(fakeCredPass))
		})

		It("forwards only allowed request headers", func() {
			resp, _ := do(http.MethodGet, e.proxy1.URL+"/v2/"+e.aliasA+"/python/python/manifests/3", e.token(), nil,
				withHeader("Accept", "application/vnd.oci.image.manifest.v1+json"),
				withHeader("User-Agent", "kaniko/v1.24.0"),
				withHeader("X-Forwarded-For", "10.0.0.1"),
				withHeader("X-Custom", "1"))
			Expect(resp.StatusCode).To(Equal(http.StatusOK))
			reqs := e.regA.recorded()
			h := reqs[len(reqs)-1].Header
			Expect(h.Get("Accept")).To(Equal("application/vnd.oci.image.manifest.v1+json"))
			Expect(h.Get("User-Agent")).To(Equal("kaniko/v1.24.0"))
			Expect(h.Get("X-Forwarded-For")).To(BeEmpty())
			Expect(h.Get("X-Custom")).To(BeEmpty())
		})

		// HTTP/2 禁止连接相关的头，上游的逐跳头透传会让严格的客户端（curl）判定为协议错误
		It("drops hop-by-hop headers for HTTP/2 clients", func() {
			h2 := httptest.NewUnstartedServer(e.proxy1.Config.Handler)
			h2.EnableHTTP2 = true
			h2.StartTLS()
			DeferCleanup(h2.Close)

			req, _ := http.NewRequest(http.MethodGet, h2.URL+"/v2/"+e.aliasA+"/python/python/manifests/3", nil)
			req.SetBasicAuth("bkpaas-build", e.token())
			resp, err := h2.Client().Do(req)
			Expect(err).NotTo(HaveOccurred())
			defer func() { _ = resp.Body.Close() }()
			Expect(resp.ProtoMajor).To(Equal(2))
			Expect(resp.StatusCode).To(Equal(http.StatusOK))
			for _, h := range []string{"Connection", "Keep-Alive", "X-Hop"} {
				Expect(resp.Header.Get(h)).To(BeEmpty())
			}
		})

		It("re-authenticates after the upstream revokes its token", func() {
			tok := e.token()
			path := e.proxy1.URL + "/v2/" + e.aliasA + "/python/python/manifests/3"
			resp, _ := do(http.MethodGet, path, tok, nil)
			Expect(resp.StatusCode).To(Equal(http.StatusOK))
			resp, _ = do(http.MethodHead, path, tok, nil)
			Expect(resp.StatusCode).To(Equal(http.StatusOK))
			Expect(e.regA.tokenRequests()).To(Equal(1))

			e.regA.revokeTokens()
			resp, body := do(http.MethodGet, path, tok, nil)
			Expect(resp.StatusCode).To(Equal(http.StatusOK))
			Expect(string(body)).To(Equal(`{"schemaVersion":2}`))
			Expect(e.regA.tokenRequests()).To(Equal(2))

			By("not retrying a request with a body, but re-authenticating the next one")
			put := e.proxy1.URL + "/v2/" + e.aliasA + "/bkpaas/app/manifests/v1"
			resp, _ = do(http.MethodPut, put, tok, []byte(`{"a":1}`))
			Expect(resp.StatusCode).To(Equal(http.StatusCreated))
			e.regA.revokeTokens()
			resp, body = do(http.MethodPut, put, tok, []byte(`{"a":1}`))
			assertProxyError(resp, body, http.StatusBadGateway, "upstream_auth_failed")
			assertNoLeak(e, resp, body)
			resp, _ = do(http.MethodPut, put, tok, []byte(`{"a":1}`))
			Expect(resp.StatusCode).To(Equal(http.StatusCreated))
		})
	})

	Describe("blob download", func() {
		It("passes 307 through and streams direct responses", func() {
			content := bytes.Repeat([]byte("layer"), 100000)
			d := e.regA.putBlob("python/python", content)
			e.regB.putBlob("python/python", content)
			e.regA.setRedirectBlobs(true)

			resp, body := do(http.MethodGet, e.proxy1.URL+"/v2/"+e.aliasA+"/python/python/blobs/"+d, e.token(), nil)
			Expect(resp.StatusCode).To(Equal(http.StatusTemporaryRedirect))
			Expect(resp.Header.Get("Location")).To(HavePrefix(e.regA.storage.URL + "/bucket/"))
			assertNoLeak(e, resp, body)

			resp, body = do(http.MethodGet, e.proxy1.URL+"/v2/"+e.aliasB+"/python/python/blobs/"+d, e.token(), nil)
			Expect(resp.StatusCode).To(Equal(http.StatusOK))
			Expect(body).To(Equal(content))

			entries := e.audit.entries()
			storageHost, _ := url.Parse(e.regA.storage.URL)
			Expect(entries[0].RedirectHost).To(Equal(storageHost.Hostname()))
			Expect(entries[0].Reference).To(Equal(d))
			Expect(entries[1].RespBytes).To(BeEquivalentTo(len(content)))
		})

		It("keeps Content-Length for HEAD", func() {
			content := bytes.Repeat([]byte("z"), 12345)
			d := e.regB.putBlob("python/python", content)
			resp, body := do(http.MethodHead, e.proxy1.URL+"/v2/"+e.aliasB+"/python/python/blobs/"+d, e.token(), nil)
			Expect(resp.StatusCode).To(Equal(http.StatusOK))
			Expect(resp.ContentLength).To(BeEquivalentTo(len(content)))
			Expect(body).To(BeEmpty())
			Expect(resp.Header.Get("Docker-Content-Digest")).To(Equal(d))
		})

		// 客户端中途断开时，发往上游的请求随之取消，不残留连接
		It("cancels the upstream transfer when the client disconnects", func() {
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
			req, _ := http.NewRequestWithContext(ctx, http.MethodGet,
				e.proxy1.URL+"/v2/"+e.aliasB+"/python/python/blobs/sha256:x", nil)
			req.SetBasicAuth("bkpaas-build", e.token())
			resp, err := http.DefaultClient.Do(req)
			Expect(err).NotTo(HaveOccurred())
			_, _ = io.CopyN(io.Discard, resp.Body, 1<<20)
			cancel()
			_ = resp.Body.Close()

			Eventually(cancelled).WithTimeout(10 * time.Second).Should(BeClosed())
		})
	})

	Describe("upload", func() {
		var repo string

		BeforeEach(func() { repo = "/v2/" + e.aliasA + "/bkpaas/app" })

		// 同一上传会话的请求分别落到两个副本
		It("completes a chunked upload across replicas", func() {
			tok := e.token()
			chunk1, chunk2 := bytes.Repeat([]byte("a"), 1000), bytes.Repeat([]byte("b"), 500)
			d := digestOf(append(append([]byte(nil), chunk1...), chunk2...))

			resp, _ := do(http.MethodPost, e.proxy1.URL+repo+"/blobs/uploads/", tok, nil)
			loc := resp.Header.Get("Location")
			Expect(resp.StatusCode).To(Equal(http.StatusAccepted))
			Expect(loc).To(HavePrefix(repo + "/blobs/uploads/"))
			Expect(loc).NotTo(ContainSubstring("upstream-"), "upstream upload id leaked")
			Expect(loc).NotTo(ContainSubstring("_state"), "upstream upload state leaked")

			resp, _ = do(http.MethodPatch, e.proxy2.URL+loc, tok, chunk1)
			Expect(resp.StatusCode).To(Equal(http.StatusAccepted))
			loc = resp.Header.Get("Location")
			resp, _ = do(http.MethodPatch, e.proxy1.URL+loc, tok, chunk2)
			Expect(resp.StatusCode).To(Equal(http.StatusAccepted))
			loc = resp.Header.Get("Location")
			resp, _ = do(http.MethodPut, e.proxy2.URL+withQuery(loc, "digest", d), tok, nil)
			Expect(resp.StatusCode).To(Equal(http.StatusCreated))
			Expect(resp.Header.Get("Location")).To(Equal(repo + "/blobs/" + d))

			By("rejecting kaniko's DELETE of the upload session")
			resp, body := do(http.MethodDelete, e.proxy1.URL+loc, tok, nil)
			assertProxyError(resp, body, http.StatusForbidden, "delete_not_allowed")

			for _, entry := range e.audit.entries() {
				if entry.Route == "upload" {
					Expect(entry.Reference).NotTo(ContainSubstring("."), "audit leaks upload session")
				}
			}
		})

		It("rejects forged sessions and sessions used in another repository", func() {
			tok := e.token()
			resp, body := do(http.MethodPatch, e.proxy1.URL+repo+"/blobs/uploads/forged.session", tok, []byte("x"))
			assertProxyError(resp, body, http.StatusForbidden, "invalid_upload_session")

			resp, _ = do(http.MethodPost, e.proxy1.URL+repo+"/blobs/uploads/", tok, nil)
			session := strings.TrimPrefix(resp.Header.Get("Location"), repo+"/blobs/uploads/")
			session, _, _ = strings.Cut(session, "?")
			resp, body = do(http.MethodPatch, e.proxy1.URL+repo+"/cache/blobs/uploads/"+session, tok, []byte("x"))
			assertProxyError(resp, body, http.StatusForbidden, "invalid_upload_session")
		})

		It("rejects an upload Location on a foreign host", func() {
			e.regA.setIntercept(func(w http.ResponseWriter, r *http.Request) bool {
				if r.Method != http.MethodPost || !strings.HasSuffix(r.URL.Path, "/blobs/uploads/") {
					return false
				}
				w.Header().Set("Location", "https://storage.example.com/v2/bkpaas/app/blobs/uploads/u1")
				w.WriteHeader(http.StatusAccepted)
				return true
			})
			resp, body := do(http.MethodPost, e.proxy1.URL+repo+"/blobs/uploads/", e.token(), nil)
			assertProxyError(resp, body, http.StatusBadGateway, "upstream_unreachable")
			Expect(resp.Header.Get("Location")).NotTo(ContainSubstring("storage.example.com"))
		})

		Describe("mount", func() {
			var d, target string

			BeforeEach(func() {
				d = e.regB.putBlob("python/python", []byte("base-layer"))
				e.regA.putBlob("python/python", []byte("base-layer"))
				e.regA.putBlob("bkpaas/other", []byte("base-layer"))
				target = e.proxy1.URL + repo + "/blobs/uploads/"
			})

			expectNoMountReachedA := func() {
				GinkgoHelper()
				for _, r := range e.regA.recorded() {
					Expect(r.Query).NotTo(ContainSubstring("mount"), "upstream A received mount request")
					Expect(r.Query).NotTo(ContainSubstring("from"), "upstream A received mount request")
				}
			}

			DescribeTable("downgrades to a plain upload",
				func(query func() string) {
					resp, _ := do(http.MethodPost, target+query(), e.token(), nil)
					Expect(resp.StatusCode).To(Equal(http.StatusAccepted))
					expectNoMountReachedA()
				},
				Entry("source on another upstream", func() string { return "?mount=" + d + "&from=" + e.aliasB + "/python/python" }),
				Entry("source denied by pull_deny", func() string { return "?mount=" + d + "&from=" + e.aliasA + "/bkpaas/other" }),
				// 缺少 from 的 mount 在部分 registry 上表示从凭证可读的任意仓库挂载
				Entry("mount without from", func() string { return "?mount=" + d }),
				Entry("from without mount", func() string { return "?from=" + e.aliasA + "/python/python" }),
			)

			It("forwards a readable same-upstream mount with the alias stripped from from", func() {
				resp, _ := do(http.MethodPost, target+"?mount="+d+"&from="+e.aliasA+"/python/python", e.token(), nil)
				Expect(resp.StatusCode).To(Equal(http.StatusCreated))
				Expect(resp.Header.Get("Location")).To(Equal(repo + "/blobs/" + d))
				reqs := e.regA.recorded()
				q, _ := url.ParseQuery(reqs[len(reqs)-1].Query)
				Expect(q.Get("from")).To(Equal("python/python"))
			})
		})
	})

	Describe("rejected requests", func() {
		DescribeTable("never reach upstream",
			func(method, path string, token func() string, status int, deny string) {
				resp, body := do(method, e.proxy1.URL+strings.ReplaceAll(path, "{A}", e.aliasA), token(), nil)
				assertProxyError(resp, body, status, deny)
				Expect(e.regA.recorded()).To(BeEmpty())
				for _, entry := range e.audit.entries() {
					Expect(entry.Deny).NotTo(BeEmpty(), "rejected request audited without deny")
				}
			},
			Entry("no token", http.MethodGet, "/v2/{A}/python/python/manifests/3",
				func() string { return "" }, 401, "token_missing"),
			Entry("expired token", http.MethodGet, "/v2/{A}/python/python/manifests/3", func() string {
				return e.token(func(c jwt.MapClaims) {
					c["exp"] = time.Now().Add(-time.Hour).Unix()
					c["iat"] = time.Now().Add(-2 * time.Hour).Unix()
				})
			}, 401, "token_expired"),
			Entry("unknown upstream", http.MethodGet, "/v2/docker-io/library/python/manifests/3",
				validToken, 403, "unknown_upstream"),
			Entry("alias written as host", http.MethodGet, "/v2/mirrors.example.com/python/python/manifests/3",
				validToken, 403, "unknown_upstream"),
			Entry("delete manifest", http.MethodDelete, "/v2/{A}/bkpaas/app/manifests/v1", validToken, 403, "delete_not_allowed"),
			Entry("delete blob", http.MethodDelete, "/v2/{A}/bkpaas/app/blobs/sha256:x", validToken, 403, "delete_not_allowed"),
			Entry("tag not granted", http.MethodPut, "/v2/{A}/bkpaas/app/manifests/latest", validToken, 403, "tag_not_granted"),
			Entry("push not granted", http.MethodPost, "/v2/{A}/bkpaas/other/blobs/uploads/", validToken, 403, "push_not_granted"),
			Entry("pull denied", http.MethodGet, "/v2/{A}/bkpaas/other/manifests/v1", validToken, 403, "pull_denied"),
			Entry("catalog", http.MethodGet, "/v2/_catalog", validToken, 404, "route_not_found"),
			Entry("non v2", http.MethodGet, "/api/v2.0/projects", validToken, 404, "route_not_found"),
			Entry("unsupported ping method", http.MethodPost, "/v2/", validToken, 404, "route_not_found"),
			Entry("unsupported route method", http.MethodPost, "/v2/{A}/python/python/manifests/3",
				validToken, 404, "route_not_found"),
			Entry("upper-case repository", http.MethodGet, "/v2/{A}/Python/python/manifests/3",
				validToken, 404, "route_not_found"),
			Entry("alias without repository", http.MethodGet, "/v2/{A}/manifests/3", validToken, 404, "route_not_found"),
			Entry("dot-dot reference", http.MethodGet, "/v2/{A}/python/python/manifests/..", validToken, 404, "route_not_found"),
			Entry("encoded dot-dot", http.MethodGet, "/v2/{A}/python/python/manifests/%2e%2e", validToken, 404, "route_not_found"),
			Entry("encoded slash", http.MethodGet, "/v2/{A}/python%2Fpython/manifests/3", validToken, 404, "route_not_found"),
			Entry("tag as blob digest", http.MethodGet, "/v2/{A}/python/python/blobs/latest", validToken, 404, "route_not_found"),
			Entry("invalid digest", http.MethodGet, "/v2/{A}/python/python/blobs/sha256:..", validToken, 404, "route_not_found"),
		)

		It("returns no body for HEAD", func() {
			resp, body := do(http.MethodHead, e.proxy1.URL+"/v2/"+e.aliasA+"/bkpaas/other/manifests/v1", e.token(), nil)
			Expect(resp.StatusCode).To(Equal(http.StatusForbidden))
			Expect(body).To(BeEmpty())
		})
	})

	Describe("upstream failures", func() {
		It("returns 502 without leaking upstream error details", func() {
			e.regA.setIntercept(func(w http.ResponseWriter, r *http.Request) bool {
				if r.URL.Path != "/token" {
					return false
				}
				http.Error(w, "invalid credential for robot:"+fakeCredPass, http.StatusUnauthorized)
				return true
			})
			resp, body := do(http.MethodGet, e.proxy1.URL+"/v2/"+e.aliasA+"/python/python/manifests/3", e.token(), nil)
			assertProxyError(resp, body, http.StatusBadGateway, "upstream_auth_failed")
			assertNoLeak(e, resp, body)
		})

		It("returns 502 when the upstream is unreachable", func() {
			e.regB.Close()
			path := e.proxy1.URL + "/v2/" + e.aliasB + "/python/python/manifests/3"
			resp, body := do(http.MethodGet, path, e.token(), nil)
			assertProxyError(resp, body, http.StatusBadGateway, "upstream_unreachable")
			resp, _ = do(http.MethodHead, path, e.token(), nil)
			Expect(resp.StatusCode).To(Equal(http.StatusBadGateway))
		})
	})

	It("rewrites the Link header of tags/list", func() {
		resp, _ := do(http.MethodGet, e.proxy1.URL+"/v2/"+e.aliasA+"/python/python/tags/list", e.token(), nil)
		Expect(resp.StatusCode).To(Equal(http.StatusOK))
		Expect(resp.Header.Get("Link")).To(Equal(`</v2/` + e.aliasA + `/python/python/tags/list?last=v1&n=1>; rel="next"`))
	})
})

type allowAll struct{}

func (allowAll) Authorize(proxy.Principal, string, oci.Route) proxy.Decision { return proxy.Decision{} }

// 授权钩子放行一切时，DELETE、未配置的上游与跨上游 mount 仍然不会到达上游
var _ = Describe("Server with a permissive authorizer", func() {
	It("still enforces defense in depth", func() {
		e := newTestEnv(func(o *proxy.Options) { o.Authorizer = allowAll{} })
		tok := e.token()
		a := e.proxy1.URL + "/v2/" + e.aliasA

		for _, u := range []string{a + "/bkpaas/app/manifests/v1", a + "/bkpaas/app/blobs/sha256:x"} {
			resp, body := do(http.MethodDelete, u, tok, nil)
			assertProxyError(resp, body, http.StatusForbidden, "delete_not_allowed")
		}
		resp, body := do(http.MethodGet, e.proxy1.URL+"/v2/docker-io/library/python/manifests/3", tok, nil)
		assertProxyError(resp, body, http.StatusForbidden, "unknown_upstream")
		resp, body = do(http.MethodGet, e.proxy1.URL+"/v2/_catalog", tok, nil)
		assertProxyError(resp, body, http.StatusNotFound, "route_not_found")
		Expect(e.regA.recorded()).To(BeEmpty())

		d := e.regB.putBlob("python/python", []byte("x"))
		resp, _ = do(http.MethodPost, a+"/bkpaas/app/blobs/uploads/?mount="+d+"&from="+e.aliasB+"/python/python", tok, nil)
		Expect(resp.StatusCode).To(Equal(http.StatusAccepted))
		for _, r := range e.regA.recorded() {
			Expect(r.Query).NotTo(ContainSubstring("from"), "upstream A received mount request")
		}
	})
})

var _ = Describe("JSONAuditor", func() {
	It("reports write failures without blocking requests", func() {
		var failures atomic.Int32
		auditor := proxy.NewJSONAuditor(failingWriter{})
		auditor.OnError = func(error) { failures.Add(1) }
		e := newTestEnv(func(o *proxy.Options) { o.Auditor = auditor })

		resp, _ := do(http.MethodGet, e.proxy1.URL+"/v2/", e.token(), nil)
		Expect(resp.StatusCode).To(Equal(http.StatusOK))
		Expect(failures.Load()).To(BeEquivalentTo(1))
	})
})

type failingWriter struct{}

func (failingWriter) Write([]byte) (int, error) { return 0, errors.New("disk full") }
