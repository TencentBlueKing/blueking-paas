package upstream

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

// fakeTokenRegistry 模拟一个 Bearer 认证的上游：/v2/ 返回的质询带一个与请求无关的 scope
type fakeTokenRegistry struct {
	*httptest.Server
	tokenRequests atomic.Int32
	lastScopes    atomic.Value
	expiresIn     int
}

func newFakeTokenRegistry() *fakeTokenRegistry {
	f := &fakeTokenRegistry{expiresIn: 300}
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
			if !ok || user != "robot" || pass != "secret" {
				w.WriteHeader(http.StatusUnauthorized)
				return
			}
			token := "tk-" + strings.Join(r.URL.Query()["scope"], "+")
			_ = json.NewEncoder(w).Encode(map[string]any{"token": token, "expires_in": f.expiresIn})
		default:
			http.NotFound(w, r)
		}
	}))
	DeferCleanup(f.Close)
	return f
}

func newTestUpstream(rawURL string, cred *Credential) *Upstream {
	u, _ := url.Parse(rawURL)
	creds := map[string]Credential{}
	if cred != nil {
		creds[u.Host] = *cred
	}
	ups, err := FromSpecs([]Spec{{Alias: "fake", URL: u}}, creds, Options{TokenMaxTTL: 10 * time.Minute})
	Expect(err).NotTo(HaveOccurred())
	return ups["fake"]
}

var robot = &Credential{Username: "robot", Password: "secret"}

func pullScope(repo string) []Scope { return []Scope{{Repo: repo, Actions: []string{"pull"}}} }

var _ = Describe("Upstream.Authorization", func() {
	ctx := context.Background()

	Context("with a Bearer upstream", func() {
		var (
			reg *fakeTokenRegistry
			up  *Upstream
		)

		BeforeEach(func() {
			reg = newFakeTokenRegistry()
			up = newTestUpstream(reg.URL, robot)
		})

		It("requests the proxy-computed scope and ignores the challenge scope", func() {
			h, hit, err := up.Authorization(ctx, []Scope{{Repo: "bkpaas/app", Actions: []string{"pull", "push"}}})
			Expect(err).NotTo(HaveOccurred())
			Expect(hit).To(BeFalse())
			Expect(h).To(Equal("Bearer tk-repository:bkpaas/app:pull,push"))
			Expect(reg.lastScopes.Load()).To(Equal([]string{"repository:bkpaas/app:pull,push"}))
		})

		It("caches by scope and refetches after Invalidate", func() {
			scopes := pullScope("python/python")
			for i := range 3 {
				_, hit, err := up.Authorization(ctx, scopes)
				Expect(err).NotTo(HaveOccurred())
				Expect(hit).To(Equal(i > 0))
			}
			Expect(reg.tokenRequests.Load()).To(BeEquivalentTo(1))

			_, hit, _ := up.Authorization(ctx, pullScope("other/repo"))
			Expect(hit).To(BeFalse(), "different scope must not hit cache")

			up.Invalidate(scopes)
			_, hit, _ = up.Authorization(ctx, scopes)
			Expect(hit).To(BeFalse(), "invalidated scope must not hit cache")
			Expect(reg.tokenRequests.Load()).To(BeEquivalentTo(3))
		})

		It("expires the cache at 90% of expires_in", func() {
			reg.expiresIn = 100
			now := time.Now()
			up.now = func() time.Time { return now }
			scopes := pullScope("a/b")

			_, _, _ = up.Authorization(ctx, scopes)
			now = now.Add(89 * time.Second)
			_, hit, _ := up.Authorization(ctx, scopes)
			Expect(hit).To(BeTrue())
			now = now.Add(2 * time.Second)
			_, hit, _ = up.Authorization(ctx, scopes)
			Expect(hit).To(BeFalse())
		})

		It("fetches only once for concurrent misses of the same scope", func() {
			var wg sync.WaitGroup
			for range 20 {
				wg.Go(func() {
					defer GinkgoRecover()
					_, _, err := up.Authorization(ctx, pullScope("a/b"))
					Expect(err).NotTo(HaveOccurred())
				})
			}
			wg.Wait()
			Expect(reg.tokenRequests.Load()).To(BeEquivalentTo(1))
		})

		It("reports a bad credential as auth failed without leaking it", func() {
			up = newTestUpstream(reg.URL, &Credential{Username: "robot", Password: "wrong"})
			_, _, err := up.Authorization(ctx, pullScope("a/b"))
			Expect(ReasonOf(err)).To(Equal(ReasonAuthFailed))
			Expect(err.Error()).NotTo(ContainSubstring("wrong"))
		})
	})

	It("reports an unreachable upstream", func() {
		_, _, err := newTestUpstream("http://127.0.0.1:1", robot).Authorization(ctx, pullScope("a/b"))
		Expect(ReasonOf(err)).To(Equal(ReasonUnreachable))
	})

	It("refuses to send credentials to a plaintext realm of an https upstream", func() {
		srv := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("WWW-Authenticate", `Bearer realm="http://token.example/token",service="x"`)
			w.WriteHeader(http.StatusUnauthorized)
		}))
		DeferCleanup(srv.Close)
		u, _ := url.Parse(srv.URL)
		ups, err := FromSpecs([]Spec{{Alias: "fake", URL: u, SkipTLSVerify: true}},
			map[string]Credential{u.Host: *robot}, Options{TokenMaxTTL: time.Minute})
		Expect(err).NotTo(HaveOccurred())

		_, _, err = ups["fake"].Authorization(ctx, pullScope("a/b"))
		Expect(ReasonOf(err)).To(Equal(ReasonAuthFailed))
		Expect(err).To(MatchError(ContainSubstring("plaintext")))
	})

	Context("with a Basic upstream", func() {
		var basicURL string

		BeforeEach(func() {
			srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				w.Header().Set("WWW-Authenticate", `Basic realm="registry"`)
				w.WriteHeader(http.StatusUnauthorized)
			}))
			DeferCleanup(srv.Close)
			basicURL = srv.URL
		})

		It("uses the credential directly", func() {
			h, _, err := newTestUpstream(basicURL, robot).Authorization(ctx, nil)
			Expect(err).NotTo(HaveOccurred())
			Expect(h).To(Equal("Basic cm9ib3Q6c2VjcmV0"))
		})

		It("fails without a credential", func() {
			_, _, err := newTestUpstream(basicURL, nil).Authorization(ctx, nil)
			Expect(ReasonOf(err)).To(Equal(ReasonAuthFailed))
		})
	})

	Context("with an upstream that requires no auth", func() {
		var openURL string

		BeforeEach(func() {
			srv := httptest.NewServer(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {}))
			DeferCleanup(srv.Close)
			openURL = srv.URL
		})

		It("sends no Authorization without a credential", func() {
			h, _, err := newTestUpstream(openURL, nil).Authorization(ctx, nil)
			Expect(err).NotTo(HaveOccurred())
			Expect(h).To(BeEmpty())
		})

		It("uses a static registry token as Bearer", func() {
			h, _, _ := newTestUpstream(openURL, &Credential{RegistryToken: "static"}).Authorization(ctx, nil)
			Expect(h).To(Equal("Bearer static"))
		})
	})
})

var _ = Describe("tokenTTL", func() {
	up := &Upstream{maxTTL: 5 * time.Minute}

	DescribeTable("expires at 90% of expires_in, capped by maxTTL",
		func(expiresIn, want time.Duration) {
			Expect(up.tokenTTL(expiresIn)).To(Equal(want))
		},
		Entry("missing expires_in", time.Duration(0), defaultTokenExpiresIn*9/10),
		Entry("100s", 100*time.Second, 90*time.Second),
		Entry("above maxTTL", time.Hour, 5*time.Minute),
		Entry("at least one second", time.Second, time.Second),
	)
})

var _ = Describe("ScopeKey", func() {
	It("does not depend on the order of scopes and actions", func() {
		a := ScopeKey([]Scope{{Repo: "x", Actions: []string{"push", "pull"}}, {Repo: "a", Actions: []string{"pull"}}})
		b := ScopeKey([]Scope{{Repo: "a", Actions: []string{"pull"}}, {Repo: "x", Actions: []string{"pull", "push"}}})
		Expect(a).To(Equal(b))
	})
})
