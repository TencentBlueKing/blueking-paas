// bench 以独立进程启动 registry-proxy（绑定单核、GOMAXPROCS=1），对一个直接返回 blob 的模拟上游测量：
//
//   - 经代理下载、上传大 blob 的吞吐，以及代理进程 RSS 的增量；
//   - 上游 token 缓存命中时，HEAD manifest 经代理的附加延迟 P99。
//
// 用法：go run ./hack/bench -proxy-bin build/registry-proxy -size 2GiB
// 建议用 taskset 把 bench 自身绑到其他 CPU，避免与代理争抢：taskset -c 1-7 go run ./hack/bench ...
package main

import (
	"bufio"
	"bytes"
	"context"
	"crypto/ecdsa"
	"crypto/ed25519"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"flag"
	"fmt"
	"io"
	"log"
	"math/big"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync/atomic"
	"time"

	"github.com/golang-jwt/jwt/v5"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/buildtoken"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/upstream"
)

const (
	audience      = "bkpaas-registry-proxy:bench"
	upstreamToken = "bench-upstream-token"
	manifestBody  = `{"schemaVersion":2,"mediaType":"application/vnd.oci.image.manifest.v1+json"}`
)

func main() {
	proxyBin := flag.String("proxy-bin", "build/registry-proxy", "registry-proxy 可执行文件")
	sizeFlag := flag.String("size", "2GiB", "blob 大小，支持 MiB / GiB 后缀")
	cpu := flag.String("cpu", "0", "代理绑定的 CPU（taskset -c）")
	requests := flag.Int("requests", 2000, "延迟测试的请求数")
	upstreamTLS := flag.Bool("upstream-tls", true, "模拟上游使用 HTTPS（代理两侧都做 TLS，最保守）")
	chunked := flag.Bool("chunked", false, "上传时不声明 Content-Length（与 kaniko 流式上传层的方式一致）")
	flag.Parse()

	size, err := parseSize(*sizeFlag)
	if err != nil {
		log.Fatal(err)
	}
	dir, err := os.MkdirTemp("", "registry-proxy-bench-")
	if err != nil {
		log.Fatal(err)
	}
	defer func() { _ = os.RemoveAll(dir) }()

	up := startUpstream(*upstreamTLS, size)
	defer up.Close()
	upHost := strings.TrimPrefix(strings.TrimPrefix(up.URL, "https://"), "http://")
	alias, _ := upstream.AliasOf(upHost)

	token := prepareFiles(dir, upHost, alias)
	proxyAddr, adminAddr := freeAddr(), freeAddr()
	writeConfig(dir, proxyAddr, adminAddr, alias, up.URL)

	cmd := exec.Command("taskset", "-c", *cpu, *proxyBin, "-config", filepath.Join(dir, "config.yaml"))
	cmd.Env = append(os.Environ(), "GOMAXPROCS=1")
	logFile, _ := os.Create(filepath.Join(dir, "proxy.log"))
	cmd.Stderr, cmd.Stdout = logFile, io.Discard
	if err := cmd.Start(); err != nil {
		log.Fatal(err)
	}
	defer func() { _ = cmd.Process.Kill(); _ = cmd.Wait() }()
	waitReady(adminAddr, filepath.Join(dir, "proxy.log"))
	pid := cmd.Process.Pid

	client := &http.Client{Transport: &http.Transport{
		TLSClientConfig:   &tls.Config{InsecureSkipVerify: true}, //nolint:gosec
		ForceAttemptHTTP2: true,
		MaxIdleConns:      16,
	}}
	base := "https://" + proxyAddr + "/v2/" + alias + "/bench/app"
	auth := "Basic " + base64.StdEncoding.EncodeToString([]byte("bkpaas-build:"+token))

	// 预热：建立连接并填充上游 token 缓存
	for range 20 {
		closeBody(mustDo(client, "HEAD", base+"/manifests/v1", auth, nil, -1, http.StatusOK))
	}
	baseline := rssKB(pid)
	fmt.Printf("代理 pid=%d，绑定 CPU %s，GOMAXPROCS=1，基线 RSS %.1f MiB\n", pid, *cpu, float64(baseline)/1024)

	// 下载
	peak := watchRSS(pid)
	start := time.Now()
	resp := mustDo(client, "GET", base+"/blobs/sha256:"+strings.Repeat("a", 64), auth, nil, -1, http.StatusOK)
	n, _ := io.Copy(io.Discard, resp.Body)
	closeBody(resp)
	dl := time.Since(start)
	dlPeak := peak.stop()
	report("下载", n, size, dl, dlPeak, baseline)

	// 上传
	peak = watchRSS(pid)
	resp = mustDo(client, "POST", base+"/blobs/uploads/", auth, nil, 0, http.StatusAccepted)
	closeBody(resp)
	loc := resp.Header.Get("Location")
	length := size
	if *chunked {
		length = -1
	}
	start = time.Now()
	resp = mustDo(client, "PATCH", "https://"+proxyAddr+loc, auth, io.LimitReader(patternReader{}, size), length, http.StatusAccepted)
	closeBody(resp)
	ul := time.Since(start)
	ulPeak := peak.stop()
	report("上传", up.received.Load(), size, ul, ulPeak, baseline)

	// 延迟：直连上游与经代理交替进行
	upClient := &http.Client{Transport: &http.Transport{TLSClientConfig: &tls.Config{InsecureSkipVerify: true}}} //nolint:gosec
	direct := make([]time.Duration, 0, *requests)
	via := make([]time.Duration, 0, *requests)
	for range *requests {
		t0 := time.Now()
		closeBody(mustDo(upClient, "HEAD", up.URL+"/v2/bench/app/manifests/v1", "Bearer "+upstreamToken, nil, -1, http.StatusOK))
		direct = append(direct, time.Since(t0))
		t0 = time.Now()
		closeBody(mustDo(client, "HEAD", base+"/manifests/v1", auth, nil, -1, http.StatusOK))
		via = append(via, time.Since(t0))
	}
	dp50, dp99 := percentiles(direct)
	vp50, vp99 := percentiles(via)
	added := vp99 - dp99
	fmt.Printf("HEAD manifest %d 次：直连 P50 %s / P99 %s，经代理 P50 %s / P99 %s，附加延迟 P99 %s（阈值 50ms）%s\n",
		*requests, dp50, dp99, vp50, vp99, added, verdict(added <= 50*time.Millisecond))
}

func report(name string, n, size int64, d time.Duration, peakKB, baselineKB int64) {
	mbps := float64(n) / d.Seconds() / 1e6
	delta := float64(peakKB-baselineKB) / 1024
	fmt.Printf("%s %d 字节（期望 %d）：耗时 %s，吞吐 %.1f MB/s（阈值 100）%s，峰值 RSS 增量 %.1f MiB（阈值 64）%s\n",
		name, n, size, d.Round(time.Millisecond), mbps, verdict(n == size && mbps >= 100), delta, verdict(delta <= 64))
}

func verdict(ok bool) string {
	if ok {
		return "PASS"
	}
	return "FAIL"
}

type benchUpstream struct {
	*httptest.Server
	received atomic.Int64
}

// startUpstream 模拟 Bearer 认证、直接返回 blob 数据的上游
func startUpstream(useTLS bool, size int64) *benchUpstream {
	u := &benchUpstream{}
	var baseURL string
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/token" {
			_ = json.NewEncoder(w).Encode(map[string]any{"token": upstreamToken, "expires_in": 3600})
			return
		}
		if r.Header.Get("Authorization") != "Bearer "+upstreamToken {
			w.Header().Set("WWW-Authenticate", `Bearer realm="`+baseURL+`/token",service="bench"`)
			w.WriteHeader(http.StatusUnauthorized)
			return
		}
		switch {
		case r.URL.Path == "/v2/":
		case strings.Contains(r.URL.Path, "/manifests/"):
			w.Header().Set("Content-Type", "application/vnd.oci.image.manifest.v1+json")
			w.Header().Set("Content-Length", strconv.Itoa(len(manifestBody)))
			if r.Method == http.MethodGet {
				_, _ = io.WriteString(w, manifestBody)
			}
		case strings.HasSuffix(r.URL.Path, "/blobs/uploads/") && r.Method == http.MethodPost:
			w.Header().Set("Location", "/v2/bench/app/blobs/uploads/bench-upload?_state=x")
			w.WriteHeader(http.StatusAccepted)
		case strings.Contains(r.URL.Path, "/blobs/uploads/") && r.Method == http.MethodPatch:
			n, _ := io.Copy(io.Discard, r.Body)
			u.received.Store(n)
			w.Header().Set("Location", "/v2/bench/app/blobs/uploads/bench-upload?_state=y")
			w.WriteHeader(http.StatusAccepted)
		case strings.Contains(r.URL.Path, "/blobs/"):
			w.Header().Set("Content-Length", strconv.FormatInt(size, 10))
			_, _ = io.Copy(w, io.LimitReader(patternReader{}, size))
		default:
			http.NotFound(w, r)
		}
	})
	if useTLS {
		u.Server = httptest.NewTLSServer(handler)
	} else {
		u.Server = httptest.NewServer(handler)
	}
	baseURL = u.URL
	return u
}

var pattern = func() []byte {
	b := make([]byte, 1<<20)
	_, _ = rand.Read(b)
	return b
}()

// patternReader 无限重复一段随机数据，不占用与 blob 大小相关的内存
type patternReader struct{}

func (patternReader) Read(p []byte) (int, error) {
	n := 0
	for n < len(p) {
		n += copy(p[n:], pattern)
	}
	return n, nil
}

func prepareFiles(dir, upHost, alias string) string {
	pub, priv, _ := ed25519.GenerateKey(rand.Reader)
	x := base64.RawURLEncoding.EncodeToString(pub)
	kid := buildtoken.JWKThumbprint(x)
	jwks, _ := json.Marshal(map[string]any{"keys": []map[string]string{{"kty": "OKP", "crv": "Ed25519", "x": x, "kid": kid, "alg": "EdDSA", "use": "sig"}}})
	write(dir, "jwks.json", jwks)
	write(dir, "upload.key", bytes.Repeat([]byte("u"), 32))
	cfg, _ := json.Marshal(map[string]any{"auths": map[string]any{upHost: map[string]string{"username": "robot", "password": "bench"}}})
	write(dir, "upstream.json", cfg)
	cert, key := selfSignedCert()
	write(dir, "tls.crt", cert)
	write(dir, "tls.key", key)

	now := time.Now()
	claims := jwt.MapClaims{
		"iss": buildtoken.Issuer, "aud": audience, "sub": "bench", "jti": "bench", "ver": 1,
		"iat": now.Unix(), "exp": now.Add(time.Hour).Unix(), "app_code": "bench", "module": "default",
		"push": []map[string]any{{"repo": alias + "/bench/app", "tags": []string{"*"}}},
		"pull": []string{alias + "/"},
	}
	tok := jwt.NewWithClaims(jwt.SigningMethodEdDSA, claims)
	tok.Header["kid"] = kid
	s, err := tok.SignedString(priv)
	if err != nil {
		log.Fatal(err)
	}
	return s
}

func writeConfig(dir, listen, admin, alias, upURL string) {
	cfg := fmt.Sprintf(`listen: %q
admin_listen: %q
tls:
  cert_file: %s
  key_file: %s
audience: %q
jwks_file: %s
upstream_docker_config_file: %s
upload_session:
  key_file: %s
upstreams:
  - alias: %s
    url: %s
    skip_tls_verify: true
`, listen, admin, filepath.Join(dir, "tls.crt"), filepath.Join(dir, "tls.key"), audience,
		filepath.Join(dir, "jwks.json"), filepath.Join(dir, "upstream.json"), filepath.Join(dir, "upload.key"), alias, upURL)
	write(dir, "config.yaml", []byte(cfg))
}

func write(dir, name string, b []byte) {
	if err := os.WriteFile(filepath.Join(dir, name), b, 0o600); err != nil {
		log.Fatal(err)
	}
}

func selfSignedCert() ([]byte, []byte) {
	key, _ := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	tmpl := &x509.Certificate{
		SerialNumber: big.NewInt(1),
		Subject:      pkix.Name{CommonName: "registry-proxy-bench"},
		NotBefore:    time.Now().Add(-time.Hour),
		NotAfter:     time.Now().Add(24 * time.Hour),
		IPAddresses:  []net.IP{net.ParseIP("127.0.0.1")},
	}
	der, err := x509.CreateCertificate(rand.Reader, tmpl, tmpl, &key.PublicKey, key)
	if err != nil {
		log.Fatal(err)
	}
	kd, _ := x509.MarshalECPrivateKey(key)
	return pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der}), pem.EncodeToMemory(&pem.Block{Type: "EC PRIVATE KEY", Bytes: kd})
}

func freeAddr() string {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		log.Fatal(err)
	}
	defer func() { _ = ln.Close() }()
	return ln.Addr().String()
}

func waitReady(admin, logPath string) {
	for range 100 {
		if resp, err := http.Get("http://" + admin + "/readyz"); err == nil {
			closeBody(resp)
			if resp.StatusCode == http.StatusOK {
				return
			}
		}
		time.Sleep(100 * time.Millisecond)
	}
	b, _ := os.ReadFile(logPath)
	log.Fatalf("proxy not ready:\n%s", b)
}

func mustDo(c *http.Client, method, url, auth string, body io.Reader, length int64, want int) *http.Response {
	req, err := http.NewRequestWithContext(context.Background(), method, url, body)
	if err != nil {
		log.Fatal(err)
	}
	if body != nil {
		req.ContentLength = length
	}
	req.Header.Set("Authorization", auth)
	resp, err := c.Do(req)
	if err != nil {
		log.Fatalf("%s %s: %v", method, url, err)
	}
	if resp.StatusCode != want {
		b, _ := io.ReadAll(resp.Body)
		log.Fatalf("%s %s: status %d, want %d: %s", method, url, resp.StatusCode, want, b)
	}
	return resp
}

func closeBody(resp *http.Response) {
	_, _ = io.Copy(io.Discard, resp.Body)
	_ = resp.Body.Close()
}

func rssKB(pid int) int64 {
	f, err := os.Open(fmt.Sprintf("/proc/%d/status", pid))
	if err != nil {
		return 0
	}
	defer func() { _ = f.Close() }()
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		if v, ok := strings.CutPrefix(sc.Text(), "VmRSS:"); ok {
			n, _ := strconv.ParseInt(strings.TrimSuffix(strings.TrimSpace(v), " kB"), 10, 64)
			return n
		}
	}
	return 0
}

type rssWatcher struct {
	peak atomic.Int64
	done chan struct{}
}

func watchRSS(pid int) *rssWatcher {
	w := &rssWatcher{done: make(chan struct{})}
	w.peak.Store(rssKB(pid))
	go func() {
		t := time.NewTicker(20 * time.Millisecond)
		defer t.Stop()
		for {
			select {
			case <-w.done:
				return
			case <-t.C:
				if v := rssKB(pid); v > w.peak.Load() {
					w.peak.Store(v)
				}
			}
		}
	}()
	return w
}

func (w *rssWatcher) stop() int64 {
	close(w.done)
	return w.peak.Load()
}

func percentiles(d []time.Duration) (time.Duration, time.Duration) {
	s := append([]time.Duration(nil), d...)
	sort.Slice(s, func(i, j int) bool { return s[i] < s[j] })
	at := func(p float64) time.Duration {
		return s[min(len(s)-1, int(float64(len(s))*p))].Round(10 * time.Microsecond)
	}
	return at(0.5), at(0.99)
}

func parseSize(s string) (int64, error) {
	mult := int64(1)
	switch {
	case strings.HasSuffix(s, "GiB"):
		mult, s = 1<<30, strings.TrimSuffix(s, "GiB")
	case strings.HasSuffix(s, "MiB"):
		mult, s = 1<<20, strings.TrimSuffix(s, "MiB")
	}
	n, err := strconv.ParseInt(s, 10, 64)
	return n * mult, err
}
