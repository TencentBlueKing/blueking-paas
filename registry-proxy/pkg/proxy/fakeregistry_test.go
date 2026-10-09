package proxy_test

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"

	. "github.com/onsi/ginkgo/v2"
)

// fakeRegistry 是一个内存中的 OCI 仓库，按 Docker token 规范做 Bearer 认证，并记录收到的请求
type fakeRegistry struct {
	*httptest.Server

	mu        sync.Mutex
	tokens    map[string]bool
	tokenReqs int
	requests  []recordedRequest
	manifests map[string][]byte // repo:ref
	blobs     map[string][]byte // repo@digest
	uploads   map[string][]byte // upload id
	// redirectBlobs 为 true 时 blob 下载返回 307 到对象存储，否则由上游直接返回数据
	redirectBlobs bool
	// storage 模拟对象存储，只提供 307 的目标地址；代理不跟随重定向，测试中不会访问它
	storage *httptest.Server
	// intercept 返回 true 表示已处理请求，用于模拟上游的异常行为
	intercept func(http.ResponseWriter, *http.Request) bool
}

type recordedRequest struct {
	Method        string
	Path          string
	Query         string
	Authorization string
	Cookie        string
	Header        http.Header
}

const fakeCredUser, fakeCredPass = "robot", "upstream-secret-password"

func newFakeRegistry() *fakeRegistry {
	f := &fakeRegistry{
		tokens:    map[string]bool{},
		manifests: map[string][]byte{},
		blobs:     map[string][]byte{},
		uploads:   map[string][]byte{},
	}
	f.storage = httptest.NewServer(http.NotFoundHandler())
	f.Server = httptest.NewServer(http.HandlerFunc(f.handle))
	DeferCleanup(func() { f.Close(); f.storage.Close() })
	return f
}

func (f *fakeRegistry) host() string { return strings.TrimPrefix(f.URL, "http://") }

func (f *fakeRegistry) revokeTokens() {
	f.mu.Lock()
	f.tokens = map[string]bool{}
	f.mu.Unlock()
}

func (f *fakeRegistry) tokenRequests() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.tokenReqs
}

func (f *fakeRegistry) recorded() []recordedRequest {
	f.mu.Lock()
	defer f.mu.Unlock()
	return append([]recordedRequest(nil), f.requests...)
}

func (f *fakeRegistry) putBlob(repo string, content []byte) string {
	d := digestOf(content)
	f.mu.Lock()
	f.blobs[repo+"@"+d] = content
	f.mu.Unlock()
	return d
}

func (f *fakeRegistry) setRedirectBlobs(v bool) {
	f.mu.Lock()
	f.redirectBlobs = v
	f.mu.Unlock()
}

func (f *fakeRegistry) setIntercept(fn func(http.ResponseWriter, *http.Request) bool) {
	f.mu.Lock()
	f.intercept = fn
	f.mu.Unlock()
}

func (f *fakeRegistry) putManifest(repo, ref string, body []byte) {
	f.mu.Lock()
	f.manifests[repo+":"+ref] = body
	f.mu.Unlock()
}

func (f *fakeRegistry) handle(w http.ResponseWriter, r *http.Request) {
	f.mu.Lock()
	intercept := f.intercept
	f.mu.Unlock()
	if intercept != nil && intercept(w, r) {
		return
	}
	if r.URL.Path == "/token" {
		f.issueToken(w, r)
		return
	}
	f.mu.Lock()
	f.requests = append(f.requests, recordedRequest{r.Method, r.URL.Path, r.URL.RawQuery, r.Header.Get("Authorization"), r.Header.Get("Cookie"), r.Header.Clone()})
	auth, ok := strings.CutPrefix(r.Header.Get("Authorization"), "Bearer ")
	valid := ok && f.tokens[auth]
	f.mu.Unlock()
	if !valid {
		w.Header().Set("WWW-Authenticate", `Bearer realm="`+f.URL+`/token",service="fake",scope="repository:unrelated:pull"`)
		w.WriteHeader(http.StatusUnauthorized)
		return
	}
	if r.URL.Path == "/v2/" {
		return
	}
	// 上游在非 401 响应中也可能带质询、Cookie 与逐跳头（Harbor 前的 nginx 会返回 Keep-Alive），代理必须剥离
	w.Header().Set("WWW-Authenticate", `Bearer realm="`+f.URL+`/token"`)
	w.Header().Set("Set-Cookie", "sid=upstream-session; Path=/")
	w.Header().Set("Keep-Alive", "timeout=75")
	w.Header().Set("Connection", "X-Hop")
	w.Header().Set("X-Hop", "1")

	rest := strings.TrimPrefix(r.URL.Path, "/v2/")
	switch {
	case strings.Contains(rest, "/manifests/"):
		repo, ref, _ := strings.Cut(rest, "/manifests/")
		f.manifest(w, r, repo, ref)
	case strings.Contains(rest, "/blobs/uploads"):
		repo, id, _ := strings.Cut(rest, "/blobs/uploads")
		f.upload(w, r, repo, strings.Trim(id, "/"))
	case strings.Contains(rest, "/blobs/"):
		repo, d, _ := strings.Cut(rest, "/blobs/")
		f.blob(w, r, repo, d)
	case strings.HasSuffix(rest, "/tags/list"):
		repo := strings.TrimSuffix(rest, "/tags/list")
		w.Header().Set("Link", `</v2/`+repo+`/tags/list?last=v1&n=1>; rel="next"`)
		_ = json.NewEncoder(w).Encode(map[string]any{"name": repo, "tags": []string{"v1"}})
	default:
		http.NotFound(w, r)
	}
}

func (f *fakeRegistry) issueToken(w http.ResponseWriter, r *http.Request) {
	user, pass, _ := r.BasicAuth()
	f.mu.Lock()
	defer f.mu.Unlock()
	f.tokenReqs++
	if user != fakeCredUser || pass != fakeCredPass {
		w.WriteHeader(http.StatusUnauthorized)
		return
	}
	tok := randomHex(16)
	f.tokens[tok] = true
	_ = json.NewEncoder(w).Encode(map[string]any{"token": tok, "expires_in": 300})
}

func (f *fakeRegistry) manifest(w http.ResponseWriter, r *http.Request, repo, ref string) {
	key := repo + ":" + ref
	switch r.Method {
	case http.MethodPut:
		body, _ := io.ReadAll(r.Body)
		f.mu.Lock()
		f.manifests[key] = body
		f.manifests[repo+":"+digestOf(body)] = body
		f.mu.Unlock()
		w.Header().Set("Location", f.URL+"/v2/"+repo+"/manifests/"+digestOf(body))
		w.Header().Set("Docker-Content-Digest", digestOf(body))
		w.WriteHeader(http.StatusCreated)
	default:
		f.mu.Lock()
		body, ok := f.manifests[key]
		f.mu.Unlock()
		if !ok {
			http.Error(w, `{"errors":[{"code":"MANIFEST_UNKNOWN"}]}`, http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", "application/vnd.oci.image.manifest.v1+json")
		w.Header().Set("Docker-Content-Digest", digestOf(body))
		w.Header().Set("Content-Length", fmt.Sprint(len(body)))
		if r.Method == http.MethodGet {
			_, _ = w.Write(body)
		}
	}
}

func (f *fakeRegistry) blob(w http.ResponseWriter, r *http.Request, repo, d string) {
	f.mu.Lock()
	body, ok := f.blobs[repo+"@"+d]
	redirect := f.redirectBlobs
	f.mu.Unlock()
	if !ok {
		http.Error(w, `{"errors":[{"code":"BLOB_UNKNOWN"}]}`, http.StatusNotFound)
		return
	}
	if redirect {
		w.Header().Set("Location", f.storage.URL+"/bucket/"+d+"?X-Signature=abc")
		w.WriteHeader(http.StatusTemporaryRedirect)
		return
	}
	w.Header().Set("Content-Length", fmt.Sprint(len(body)))
	w.Header().Set("Docker-Content-Digest", d)
	if r.Method == http.MethodGet {
		_, _ = w.Write(body)
	}
}

func (f *fakeRegistry) upload(w http.ResponseWriter, r *http.Request, repo, id string) {
	q := r.URL.Query()
	switch {
	case r.Method == http.MethodPost && id == "":
		if mount, from := q.Get("mount"), q.Get("from"); mount != "" && from != "" {
			f.mu.Lock()
			body, ok := f.blobs[from+"@"+mount]
			if ok {
				f.blobs[repo+"@"+mount] = body
			}
			f.mu.Unlock()
			if ok {
				w.Header().Set("Location", f.URL+"/v2/"+repo+"/blobs/"+mount)
				w.WriteHeader(http.StatusCreated)
				return
			}
		}
		id := "upstream-" + randomHex(8)
		f.mu.Lock()
		f.uploads[id] = nil
		f.mu.Unlock()
		w.Header().Set("Location", "/v2/"+repo+"/blobs/uploads/"+id+"?_state=s0")
		w.Header().Set("Docker-Upload-UUID", id)
		w.WriteHeader(http.StatusAccepted)
	case r.Method == http.MethodPatch:
		body, _ := io.ReadAll(r.Body)
		f.mu.Lock()
		cur, ok := f.uploads[id]
		f.uploads[id] = append(cur, body...)
		n := len(f.uploads[id])
		f.mu.Unlock()
		if !ok || q.Get("_state") == "" {
			http.Error(w, "unknown upload", http.StatusNotFound)
			return
		}
		w.Header().Set("Location", f.URL+"/v2/"+repo+"/blobs/uploads/"+id+"?_state=s"+fmt.Sprint(n))
		w.Header().Set("Range", fmt.Sprintf("0-%d", n-1))
		w.WriteHeader(http.StatusAccepted)
	case r.Method == http.MethodPut:
		body, _ := io.ReadAll(r.Body)
		f.mu.Lock()
		content, ok := f.uploads[id]
		content = append(content, body...)
		delete(f.uploads, id)
		f.mu.Unlock()
		d := q.Get("digest")
		if !ok || d != digestOf(content) {
			http.Error(w, `{"errors":[{"code":"DIGEST_INVALID"}]}`, http.StatusBadRequest)
			return
		}
		f.putBlob(repo, content)
		w.Header().Set("Location", f.URL+"/v2/"+repo+"/blobs/"+d)
		w.WriteHeader(http.StatusCreated)
	default:
		http.Error(w, "unsupported", http.StatusMethodNotAllowed)
	}
}

func digestOf(b []byte) string {
	sum := sha256.Sum256(b)
	return "sha256:" + hex.EncodeToString(sum[:])
}

func randomHex(n int) string {
	b := make([]byte, n)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}
