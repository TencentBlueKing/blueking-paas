package upstream

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

// fakeTokenRegistry 模拟一个 Bearer 认证的上游：/v2/ 返回的质询带一个与请求无关的 scope
type fakeTokenRegistry struct {
	*httptest.Server
	tokenRequests atomic.Int32
	lastScopes    atomic.Value
	expiresIn     int
	tokenStatus   int
}

func newFakeTokenRegistry(t *testing.T) *fakeTokenRegistry {
	t.Helper()
	f := &fakeTokenRegistry{expiresIn: 300, tokenStatus: http.StatusOK}
	f.Server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/v2/":
			w.Header().Set("WWW-Authenticate",
				`Bearer realm="`+f.URL+`/token",service="fake",scope="repository:unrelated/repo:pull"`)
			w.WriteHeader(http.StatusUnauthorized)
		case "/token":
			f.tokenRequests.Add(1)
			f.lastScopes.Store(r.URL.Query()["scope"])
			user, pass, ok := r.BasicAuth()
			if f.tokenStatus != http.StatusOK || !ok || user != "robot" || pass != "secret" {
				w.WriteHeader(max(f.tokenStatus, http.StatusUnauthorized))
				return
			}
			_ = json.NewEncoder(w).Encode(map[string]any{"token": "tk-" + strings.Join(r.URL.Query()["scope"], "+"), "expires_in": f.expiresIn})
		default:
			http.NotFound(w, r)
		}
	}))
	t.Cleanup(f.Close)
	return f
}

func newTestUpstream(t *testing.T, rawURL string, cred *Credential) *Upstream {
	t.Helper()
	u, _ := url.Parse(rawURL)
	creds := map[string]Credential{}
	if cred != nil {
		creds[u.Host] = *cred
	}
	ups, err := FromSpecs([]Spec{{Alias: "fake", URL: u}}, creds, Options{TokenMaxTTL: 10 * time.Minute})
	if err != nil {
		t.Fatal(err)
	}
	return ups["fake"]
}

var robot = &Credential{Username: "robot", Password: "secret"}

func TestBearerUsesProxyComputedScope(t *testing.T) {
	reg := newFakeTokenRegistry(t)
	up := newTestUpstream(t, reg.URL, robot)
	scopes := []Scope{{Repo: "bkpaas/app", Actions: []string{"pull", "push"}}}

	h, hit, err := up.Authorization(context.Background(), scopes)
	if err != nil || hit {
		t.Fatalf("first lookup: hit=%v err=%v", hit, err)
	}
	if h != "Bearer tk-repository:bkpaas/app:pull,push" {
		t.Fatalf("header = %q", h)
	}
	got := reg.lastScopes.Load().([]string)
	if len(got) != 1 || got[0] != "repository:bkpaas/app:pull,push" {
		t.Fatalf("token request scopes = %v, the challenge scope must be ignored", got)
	}
}

func TestAuthorizationCacheAndInvalidate(t *testing.T) {
	reg := newFakeTokenRegistry(t)
	up := newTestUpstream(t, reg.URL, robot)
	scopes := []Scope{{Repo: "python/python", Actions: []string{"pull"}}}
	ctx := context.Background()

	for i := range 3 {
		if _, hit, err := up.Authorization(ctx, scopes); err != nil || hit != (i > 0) {
			t.Fatalf("lookup %d: hit=%v err=%v", i, hit, err)
		}
	}
	if n := reg.tokenRequests.Load(); n != 1 {
		t.Fatalf("token requests = %d, want 1", n)
	}
	// 不同 scope 独立缓存
	if _, hit, _ := up.Authorization(ctx, []Scope{{Repo: "other/repo", Actions: []string{"pull"}}}); hit {
		t.Fatal("different scope must not hit cache")
	}

	up.Invalidate(scopes)
	if _, hit, _ := up.Authorization(ctx, scopes); hit {
		t.Fatal("invalidated scope must not hit cache")
	}
	if n := reg.tokenRequests.Load(); n != 3 {
		t.Fatalf("token requests = %d, want 3", n)
	}
}

func TestAuthorizationExpiry(t *testing.T) {
	reg := newFakeTokenRegistry(t)
	reg.expiresIn = 100
	up := newTestUpstream(t, reg.URL, robot)
	now := time.Now()
	up.now = func() time.Time { return now }
	scopes := []Scope{{Repo: "a/b", Actions: []string{"pull"}}}

	_, _, _ = up.Authorization(context.Background(), scopes)
	now = now.Add(89 * time.Second)
	if _, hit, _ := up.Authorization(context.Background(), scopes); !hit {
		t.Fatal("token should be reused before 90% of expires_in")
	}
	now = now.Add(2 * time.Second)
	if _, hit, _ := up.Authorization(context.Background(), scopes); hit {
		t.Fatal("token should be refreshed after 90% of expires_in")
	}
}

func TestTokenTTL(t *testing.T) {
	up := &Upstream{maxTTL: 5 * time.Minute}
	cases := map[time.Duration]time.Duration{
		0:                 defaultTokenExpiresIn * 9 / 10,
		100 * time.Second: 90 * time.Second,
		time.Hour:         5 * time.Minute,
		time.Second:       time.Second,
	}
	for in, want := range cases {
		if got := up.tokenTTL(in); got != want {
			t.Errorf("tokenTTL(%s) = %s, want %s", in, got, want)
		}
	}
}

func TestConcurrentMissFetchesOnce(t *testing.T) {
	reg := newFakeTokenRegistry(t)
	up := newTestUpstream(t, reg.URL, robot)
	scopes := []Scope{{Repo: "a/b", Actions: []string{"pull"}}}
	var wg sync.WaitGroup
	for range 20 {
		wg.Go(func() {
			if _, _, err := up.Authorization(context.Background(), scopes); err != nil {
				t.Error(err)
			}
		})
	}
	wg.Wait()
	if n := reg.tokenRequests.Load(); n != 1 {
		t.Fatalf("token requests = %d, want 1", n)
	}
}

func TestAuthFailures(t *testing.T) {
	t.Run("bad credential", func(t *testing.T) {
		reg := newFakeTokenRegistry(t)
		up := newTestUpstream(t, reg.URL, &Credential{Username: "robot", Password: "wrong"})
		_, _, err := up.Authorization(context.Background(), []Scope{{Repo: "a/b", Actions: []string{"pull"}}})
		if ReasonOf(err) != ReasonAuthFailed {
			t.Fatalf("err = %v", err)
		}
		if strings.Contains(err.Error(), "wrong") {
			t.Fatal("error must not contain credentials")
		}
	})
	t.Run("unreachable", func(t *testing.T) {
		up := newTestUpstream(t, "http://127.0.0.1:1", robot)
		_, _, err := up.Authorization(context.Background(), []Scope{{Repo: "a/b", Actions: []string{"pull"}}})
		if ReasonOf(err) != ReasonUnreachable {
			t.Fatalf("err = %v", err)
		}
	})
	t.Run("plaintext realm for https upstream", func(t *testing.T) {
		srv := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("WWW-Authenticate", `Bearer realm="http://token.example/token",service="x"`)
			w.WriteHeader(http.StatusUnauthorized)
		}))
		defer srv.Close()
		u, _ := url.Parse(srv.URL)
		ups, _ := FromSpecs([]Spec{{Alias: "fake", URL: u, SkipTLSVerify: true}},
			map[string]Credential{u.Host: *robot}, Options{TokenMaxTTL: time.Minute})
		_, _, err := ups["fake"].Authorization(context.Background(), []Scope{{Repo: "a/b", Actions: []string{"pull"}}})
		var ae *AuthError
		if !errors.As(err, &ae) || ae.Reason != ReasonAuthFailed || !strings.Contains(err.Error(), "plaintext") {
			t.Fatalf("err = %v", err)
		}
	})
}

func TestBasicAndAnonymous(t *testing.T) {
	basic := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("WWW-Authenticate", `Basic realm="registry"`)
		w.WriteHeader(http.StatusUnauthorized)
	}))
	defer basic.Close()
	h, _, err := newTestUpstream(t, basic.URL, robot).Authorization(context.Background(), nil)
	if err != nil || h != "Basic cm9ib3Q6c2VjcmV0" {
		t.Fatalf("basic header = %q, err = %v", h, err)
	}
	if _, _, err := newTestUpstream(t, basic.URL, nil).Authorization(context.Background(), nil); ReasonOf(err) != ReasonAuthFailed {
		t.Fatalf("basic upstream without credential: err = %v", err)
	}

	open := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
	defer open.Close()
	if h, _, err := newTestUpstream(t, open.URL, nil).Authorization(context.Background(), nil); err != nil || h != "" {
		t.Fatalf("anonymous header = %q, err = %v", h, err)
	}
	if h, _, _ := newTestUpstream(t, open.URL, &Credential{RegistryToken: "static"}).Authorization(context.Background(), nil); h != "Bearer static" {
		t.Fatalf("registry token header = %q", h)
	}
}

func TestScopeKeyIsOrderIndependent(t *testing.T) {
	a := ScopeKey([]Scope{{Repo: "x", Actions: []string{"push", "pull"}}, {Repo: "a", Actions: []string{"pull"}}})
	b := ScopeKey([]Scope{{Repo: "a", Actions: []string{"pull"}}, {Repo: "x", Actions: []string{"pull", "push"}}})
	if a != b {
		t.Fatalf("%q != %q", a, b)
	}
}
