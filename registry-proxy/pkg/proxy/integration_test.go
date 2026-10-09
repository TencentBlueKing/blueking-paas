//go:build integration

package proxy_test

import (
	"bytes"
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/authz"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/buildtoken"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/proxy"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/upstream"
)

// 基于本地 registry:2 的集成测试，由 hack/integration.sh 启动 registry 后执行：
//
//	REGISTRY_PROXY_IT_UPSTREAM=127.0.0.1:25010 go test -tags integration ./pkg/proxy/ -ginkgo.label-filter=integration
//
// 同一个 registry 以 127.0.0.1:<port> 与 localhost:<port> 两个别名配置为两个上游，用于验证跨上游 mount 降级。
var _ = Describe("Integration with registry:2", Label("integration"), func() {
	It("pushes and pulls an image across replicas", func() {
		hostA := os.Getenv("REGISTRY_PROXY_IT_UPSTREAM")
		if hostA == "" {
			Skip("REGISTRY_PROXY_IT_UPSTREAM is not set")
		}
		_, port, _ := strings.Cut(hostA, ":")
		hostB := "localhost:" + port
		aliasA, _ := upstream.AliasOf(hostA)
		aliasB, _ := upstream.AliasOf(hostB)

		pub, priv, _ := ed25519.GenerateKey(rand.Reader)
		kid := buildtoken.JWKThumbprint(base64.RawURLEncoding.EncodeToString(pub))
		newProxy := func() *httptest.Server {
			var specs []upstream.Spec
			for alias, host := range map[string]string{aliasA: hostA, aliasB: hostB} {
				specs = append(specs, upstream.Spec{Alias: alias, URL: &url.URL{Scheme: "http", Host: host}})
			}
			ups, err := upstream.FromSpecs(specs, nil, upstream.Options{TokenMaxTTL: time.Minute})
			Expect(err).NotTo(HaveOccurred())
			srv, err := proxy.New(proxy.Options{
				Upstreams:        ups,
				Authenticator:    &authz.TokenAuthenticator{Keys: buildtoken.KeySet{kid: pub}, Audience: testAudience},
				Authorizer:       &authz.PolicyAuthorizer{Upstreams: upstream.Aliases(ups)},
				UploadSessionKey: bytes.Repeat([]byte("i"), 32),
			})
			Expect(err).NotTo(HaveOccurred())
			ts := httptest.NewServer(srv)
			DeferCleanup(ts.Close)
			return ts
		}
		p1, p2 := newProxy(), newProxy()

		suffix := randomHex(4)
		appRepo := "it-" + suffix + "/app"
		now := time.Now()
		claims := jwt.MapClaims{
			"iss": buildtoken.Issuer, "aud": testAudience, "sub": "it", "jti": "it", "ver": 1,
			"iat": now.Unix(), "exp": now.Add(time.Hour).Unix(), "app_code": "it", "module": "default",
			"push": []map[string]any{
				{"repo": aliasA + "/" + appRepo, "tags": []string{"v1"}},
				{"repo": aliasA + "/" + appRepo + "/cache", "tags": []string{"*"}},
			},
			"pull":      []string{aliasA + "/", aliasB + "/"},
			"pull_deny": []string{aliasA + "/it-" + suffix + "/"},
		}
		jt := jwt.NewWithClaims(jwt.SigningMethodEdDSA, claims)
		jt.Header["kid"] = kid
		tok, err := jt.SignedString(priv)
		Expect(err).NotTo(HaveOccurred())
		app := "/v2/" + aliasA + "/" + appRepo

		layer := make([]byte, 3<<20)
		_, _ = rand.Read(layer)
		layerDigest := digestOf(layer)
		config := []byte(`{"architecture":"amd64","os":"linux","rootfs":{"type":"layers","diff_ids":[]}}`)
		configDigest := digestOf(config)

		By("uploading the layer in three chunks across replicas")
		resp, _ := do(http.MethodPost, p1.URL+app+"/blobs/uploads/", tok, nil)
		Expect(resp.StatusCode).To(Equal(http.StatusAccepted))
		loc := resp.Header.Get("Location")
		proxies := []*httptest.Server{p2, p1, p2}
		for i, chunk := range [][]byte{layer[:1<<20], layer[1<<20 : 2<<20], layer[2<<20:]} {
			start := i << 20
			resp, body := do(http.MethodPatch, proxies[i].URL+loc, tok, chunk,
				withHeader("Content-Type", "application/octet-stream"),
				withHeader("Content-Range", fmt.Sprintf("%d-%d", start, start+len(chunk)-1)))
			Expect(resp.StatusCode).To(Equal(http.StatusAccepted), "patch chunk %d: %s", i, body)
			loc = resp.Header.Get("Location")
		}
		resp, body := do(http.MethodPut, p1.URL+withQuery(loc, "digest", layerDigest), tok, nil)
		Expect(resp.StatusCode).To(Equal(http.StatusCreated), "commit layer: %s", body)
		Expect(resp.Header.Get("Location")).To(Equal(app + "/blobs/" + layerDigest))

		By("uploading the config monolithically")
		resp, _ = do(http.MethodPost, p2.URL+app+"/blobs/uploads/", tok, nil)
		resp, body = do(http.MethodPut, p2.URL+withQuery(resp.Header.Get("Location"), "digest", configDigest), tok, config,
			withHeader("Content-Type", "application/octet-stream"))
		Expect(resp.StatusCode).To(Equal(http.StatusCreated), "monolithic config upload: %s", body)

		By("pushing the manifest only to the granted tag")
		manifest, _ := json.Marshal(map[string]any{
			"schemaVersion": 2,
			"mediaType":     "application/vnd.oci.image.manifest.v1+json",
			"config":        map[string]any{"mediaType": "application/vnd.oci.image.config.v1+json", "digest": configDigest, "size": len(config)},
			"layers":        []map[string]any{{"mediaType": "application/vnd.oci.image.layer.v1.tar", "digest": layerDigest, "size": len(layer)}},
		})
		mt := withHeader("Content-Type", "application/vnd.oci.image.manifest.v1+json")
		resp, body = do(http.MethodPut, p1.URL+app+"/manifests/v1", tok, manifest, mt)
		Expect(resp.StatusCode).To(Equal(http.StatusCreated), "push manifest: %s", body)
		resp, body = do(http.MethodPut, p1.URL+app+"/manifests/latest", tok, manifest, mt)
		assertProxyError(resp, body, http.StatusForbidden, "tag_not_granted")

		By("reading back the same digest via the proxy and directly")
		accept := withHeader("Accept", "application/vnd.oci.image.manifest.v1+json")
		resp, body = do(http.MethodGet, p2.URL+app+"/manifests/v1", tok, nil, accept)
		Expect(resp.StatusCode).To(Equal(http.StatusOK))
		resp2, body2 := do(http.MethodGet, "http://"+hostA+"/v2/"+appRepo+"/manifests/v1", "", nil, accept)
		Expect(resp.Header.Get("Docker-Content-Digest")).To(Equal(digestOf(manifest)))
		Expect(resp2.Header.Get("Docker-Content-Digest")).To(Equal(digestOf(manifest)))
		Expect(body).To(Equal(body2))
		resp, body = do(http.MethodGet, p1.URL+app+"/blobs/"+layerDigest, tok, nil)
		Expect(resp.StatusCode).To(Equal(http.StatusOK))
		Expect(body).To(Equal(layer))
		resp, body = do(http.MethodGet, p1.URL+app+"/tags/list", tok, nil)
		Expect(resp.StatusCode).To(Equal(http.StatusOK))
		Expect(string(body)).To(ContainSubstring(`"v1"`))

		By("forwarding a readable same-upstream mount")
		cache := app + "/cache/blobs/uploads/"
		resp, body = do(http.MethodPost, p1.URL+cache+"?mount="+layerDigest+"&from="+aliasA+"/"+appRepo, tok, nil)
		Expect(resp.StatusCode).To(Equal(http.StatusCreated), "same-upstream mount: %s", body)

		By("downgrading a cross-upstream mount although the same path exists upstream")
		resp, body = do(http.MethodPost, p2.URL+cache+"?mount="+layerDigest+"&from="+aliasB+"/"+appRepo, tok, nil)
		Expect(resp.StatusCode).To(Equal(http.StatusAccepted), "cross-upstream mount: %s", body)
		resp, body = do(http.MethodDelete, p2.URL+resp.Header.Get("Location"), tok, nil)
		assertProxyError(resp, body, http.StatusForbidden, "delete_not_allowed")

		By("denying other repositories under the app namespace")
		resp, body = do(http.MethodGet, p1.URL+"/v2/"+aliasA+"/it-"+suffix+"/other/manifests/v1", tok, nil)
		assertProxyError(resp, body, http.StatusForbidden, "pull_denied")
	})
})
