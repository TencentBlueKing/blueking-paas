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
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/authz"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/buildtoken"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/proxy"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/upstream"
)

// 基于本地 registry:2 的集成测试，由 hack/integration.sh 启动 registry 后执行：
//
//	REGISTRY_PROXY_IT_UPSTREAM=127.0.0.1:25010 go test -tags integration -run Integration ./pkg/proxy/
//
// 同一个 registry 以 127.0.0.1:<port> 与 localhost:<port> 两个别名配置为两个上游，用于验证跨上游 mount 降级。
func TestIntegrationRegistry(t *testing.T) {
	hostA := os.Getenv("REGISTRY_PROXY_IT_UPSTREAM")
	if hostA == "" {
		t.Skip("REGISTRY_PROXY_IT_UPSTREAM is not set")
	}
	_, port, _ := strings.Cut(hostA, ":")
	hostB := "localhost:" + port
	aliasA, _ := upstream.AliasOf(hostA)
	aliasB, _ := upstream.AliasOf(hostB)

	pub, priv, _ := ed25519.GenerateKey(rand.Reader)
	kid := buildtoken.JWKThumbprint(base64.RawURLEncoding.EncodeToString(pub))
	uploadKey := bytes.Repeat([]byte("i"), 32)
	newProxy := func() *httptest.Server {
		var specs []upstream.Spec
		for alias, host := range map[string]string{aliasA: hostA, aliasB: hostB} {
			specs = append(specs, upstream.Spec{Alias: alias, URL: &url.URL{Scheme: "http", Host: host}})
		}
		ups, err := upstream.FromSpecs(specs, nil, upstream.Options{TokenMaxTTL: time.Minute})
		if err != nil {
			t.Fatal(err)
		}
		srv, err := proxy.New(proxy.Options{
			Upstreams:        ups,
			Authenticator:    &authz.TokenAuthenticator{Keys: buildtoken.KeySet{kid: pub}, Audience: testAudience},
			Authorizer:       &authz.PolicyAuthorizer{Upstreams: upstream.Aliases(ups)},
			UploadSessionKey: uploadKey,
		})
		if err != nil {
			t.Fatal(err)
		}
		ts := httptest.NewServer(srv)
		t.Cleanup(ts.Close)
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
	if err != nil {
		t.Fatal(err)
	}
	app := "/v2/" + aliasA + "/" + appRepo

	layer := make([]byte, 3<<20)
	_, _ = rand.Read(layer)
	layerDigest := digestOf(layer)
	config := []byte(`{"architecture":"amd64","os":"linux","rootfs":{"type":"layers","diff_ids":[]}}`)
	configDigest := digestOf(config)

	// 分块上传 layer：三个分块依次落在不同副本上
	resp, _ := do(t, http.MethodPost, p1.URL+app+"/blobs/uploads/", tok, nil)
	if resp.StatusCode != http.StatusAccepted {
		t.Fatalf("start upload: %d", resp.StatusCode)
	}
	loc := resp.Header.Get("Location")
	proxies := []*httptest.Server{p2, p1, p2}
	for i, chunk := range [][]byte{layer[:1<<20], layer[1<<20 : 2<<20], layer[2<<20:]} {
		start := i << 20
		resp, body := do(t, http.MethodPatch, proxies[i].URL+loc, tok, chunk,
			withHeader("Content-Type", "application/octet-stream"),
			withHeader("Content-Range", rangeHeader(start, start+len(chunk)-1)))
		if resp.StatusCode != http.StatusAccepted {
			t.Fatalf("patch chunk %d: %d %s", i, resp.StatusCode, body)
		}
		loc = resp.Header.Get("Location")
	}
	resp, body := do(t, http.MethodPut, p1.URL+withQuery(loc, "digest", layerDigest), tok, nil)
	if resp.StatusCode != http.StatusCreated || resp.Header.Get("Location") != app+"/blobs/"+layerDigest {
		t.Fatalf("commit layer: %d Location=%q %s", resp.StatusCode, resp.Header.Get("Location"), body)
	}

	// 单次上传 config
	resp, _ = do(t, http.MethodPost, p2.URL+app+"/blobs/uploads/", tok, nil)
	resp, body = do(t, http.MethodPut, p2.URL+withQuery(resp.Header.Get("Location"), "digest", configDigest), tok, config,
		withHeader("Content-Type", "application/octet-stream"))
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("monolithic config upload: %d %s", resp.StatusCode, body)
	}

	manifest, _ := json.Marshal(map[string]any{
		"schemaVersion": 2,
		"mediaType":     "application/vnd.oci.image.manifest.v1+json",
		"config":        map[string]any{"mediaType": "application/vnd.oci.image.config.v1+json", "digest": configDigest, "size": len(config)},
		"layers":        []map[string]any{{"mediaType": "application/vnd.oci.image.layer.v1.tar", "digest": layerDigest, "size": len(layer)}},
	})
	mt := withHeader("Content-Type", "application/vnd.oci.image.manifest.v1+json")
	resp, body = do(t, http.MethodPut, p1.URL+app+"/manifests/v1", tok, manifest, mt)
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("push manifest: %d %s", resp.StatusCode, body)
	}
	resp, body = do(t, http.MethodPut, p1.URL+app+"/manifests/latest", tok, manifest, mt)
	assertProxyError(t, resp, body, http.StatusForbidden, "tag_not_granted")

	// 经代理与直连上游读回的 digest 一致
	accept := withHeader("Accept", "application/vnd.oci.image.manifest.v1+json")
	resp, body = do(t, http.MethodGet, p2.URL+app+"/manifests/v1", tok, nil, accept)
	viaProxy := resp.Header.Get("Docker-Content-Digest")
	resp2, body2 := do(t, http.MethodGet, "http://"+hostA+"/v2/"+appRepo+"/manifests/v1", "", nil, accept)
	if resp.StatusCode != http.StatusOK || viaProxy == "" || viaProxy != resp2.Header.Get("Docker-Content-Digest") ||
		viaProxy != digestOf(manifest) || !bytes.Equal(body, body2) {
		t.Fatalf("manifest digest via proxy %q, direct %q, pushed %q", viaProxy, resp2.Header.Get("Docker-Content-Digest"), digestOf(manifest))
	}
	resp, body = do(t, http.MethodGet, p1.URL+app+"/blobs/"+layerDigest, tok, nil)
	if resp.StatusCode != http.StatusOK || !bytes.Equal(body, layer) {
		t.Fatalf("pull layer: %d len=%d", resp.StatusCode, len(body))
	}
	resp, body = do(t, http.MethodGet, p1.URL+app+"/tags/list", tok, nil)
	if resp.StatusCode != http.StatusOK || !strings.Contains(string(body), `"v1"`) {
		t.Fatalf("tags list: %d %s", resp.StatusCode, body)
	}

	// 同上游、来源可读的 mount 转发给上游
	cache := app + "/cache/blobs/uploads/"
	resp, body = do(t, http.MethodPost, p1.URL+cache+"?mount="+layerDigest+"&from="+aliasA+"/"+appRepo, tok, nil)
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("same-upstream mount: %d %s", resp.StatusCode, body)
	}
	// 跨上游的 mount 降级为普通上传：registry 中确实存在同名来源，若转发了 mount 会返回 201
	resp, body = do(t, http.MethodPost, p2.URL+cache+"?mount="+layerDigest+"&from="+aliasB+"/"+appRepo, tok, nil)
	if resp.StatusCode != http.StatusAccepted {
		t.Fatalf("cross-upstream mount: %d %s, want 202 (downgraded)", resp.StatusCode, body)
	}
	resp, body = do(t, http.MethodDelete, p2.URL+resp.Header.Get("Location"), tok, nil)
	assertProxyError(t, resp, body, http.StatusForbidden, "delete_not_allowed")

	// 本应用命名空间下的其他仓库被 pull_deny
	resp, body = do(t, http.MethodGet, p1.URL+"/v2/"+aliasA+"/it-"+suffix+"/other/manifests/v1", tok, nil)
	assertProxyError(t, resp, body, http.StatusForbidden, "pull_denied")
}

func rangeHeader(start, end int) string { return fmt.Sprintf("%d-%d", start, end) }
