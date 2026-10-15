package proxy

import (
	"errors"
	"net/http"
	"net/textproto"
	"net/url"
	"strings"
	"sync"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/oci"
)

// copyBufPool 是流式回传上游响应体时使用的缓冲区，内存不随 blob 大小增长
var copyBufPool = sync.Pool{New: func() any { b := make([]byte, 64<<10); return &b }}

// responseWriter 记录响应状态码与响应体字节数，供审计与指标使用
type responseWriter struct {
	http.ResponseWriter
	status int
	bytes  int64
}

func (w *responseWriter) WriteHeader(code int) {
	if w.status != 0 {
		return
	}
	w.status = code
	w.ResponseWriter.WriteHeader(code)
}

func (w *responseWriter) Write(b []byte) (int, error) {
	if w.status == 0 {
		w.WriteHeader(http.StatusOK)
	}
	n, err := w.ResponseWriter.Write(b)
	w.bytes += int64(n)
	return n, err
}

// Flush 支持流式响应及时下发
func (w *responseWriter) Flush() {
	if f, ok := w.ResponseWriter.(http.Flusher); ok {
		f.Flush()
	}
}

// sanitizeUpstreamHeaders 清理透传给客户端的上游响应头
func sanitizeUpstreamHeaders(h http.Header, plan *forwardPlan) {
	// 逐跳头只对代理与上游之间的连接有效；HTTP/2 客户端收到 Connection、Keep-Alive 等头会判定为协议错误
	removeHopHeaders(h)
	// 上游质询指向上游 token 服务，透传会诱导客户端绕过代理；上游 Cookie 可能是代理账号的会话
	h.Del("WWW-Authenticate")
	h.Del("Set-Cookie")
	if links := h.Values("Link"); len(links) > 0 {
		out := make([]string, len(links))
		for i, l := range links {
			out[i] = rewriteLink(l, plan.upstream.URL, plan.alias)
		}
		h["Link"] = out
	}
}

// hopHeaders 是 RFC 7230 6.1 定义的逐跳头，与 net/http/httputil.ReverseProxy 的处理一致
var hopHeaders = []string{
	"Connection", "Proxy-Connection", "Keep-Alive", "Proxy-Authenticate",
	"Proxy-Authorization", "Te", "Trailer", "Transfer-Encoding", "Upgrade",
}

func removeHopHeaders(h http.Header) {
	for _, v := range h.Values("Connection") {
		for _, name := range strings.Split(v, ",") {
			if name = textproto.TrimString(name); name != "" {
				h.Del(name)
			}
		}
	}
	for _, k := range hopHeaders {
		h.Del(k)
	}
}

// rewriteLocation 改写上游响应的 Location：
//   - 上传会话（开始上传、续传、查询进度）的地址签名为会话 token，客户端无法改写或拿到其他仓库使用；
//   - 指向上游 /v2/ 的地址改写为代理的相对地址，并补回别名段；
//   - 指向其他主机的地址（如 307 到对象存储的预签名地址）原样保留。
func (s *Server) rewriteLocation(h http.Header, method string, status int, plan *forwardPlan) error {
	raw := h.Get("Location")
	if raw == "" {
		return nil
	}
	loc, err := plan.target.Parse(raw)
	if err != nil {
		return err
	}
	own := sameEndpoint(loc, plan.upstream.URL)

	if isUploadSessionResponse(plan.route, method, status) {
		if !own {
			return errors.New("upload session Location on a foreign host " + loc.Host)
		}
		// sessionExpiry 为 0（新会话）时由 sign 按有效期设置，续传时沿用原会话的过期时刻
		token, err := s.sessions.sign(uploadSession{Repo: plan.route.Repo, Location: loc.RequestURI(), Expiry: plan.sessionExpiry})
		if err != nil {
			return err
		}
		h.Set("Location", "/v2/"+plan.route.Repo+"/blobs/uploads/"+token)
		return nil
	}

	if own && strings.HasPrefix(loc.Path, "/v2/") {
		rel := url.URL{Path: plan.alias.clientPath(loc.Path), RawQuery: loc.RawQuery}
		h.Set("Location", rel.String())
	}
	return nil
}

// isUploadSessionResponse 判断响应的 Location 是否为上传会话的续传地址
func isUploadSessionResponse(rt oci.Route, method string, status int) bool {
	if rt.Kind != oci.RouteUpload {
		return false
	}
	if !rt.Session {
		return method == http.MethodPost && status == http.StatusAccepted
	}
	return status == http.StatusAccepted || status == http.StatusNoContent
}

// rewriteLink 把 Link 头（tags/list 分页）中指向上游 /v2/<repo> 的地址改写为代理的相对地址
func rewriteLink(v string, upstreamURL *url.URL, alias aliasMapping) string {
	start := strings.Index(v, "<")
	end := strings.Index(v, ">")
	if start < 0 || end < start {
		return v
	}
	u, err := url.Parse(v[start+1 : end])
	if err != nil || !strings.HasPrefix(u.Path, "/v2/") {
		return v
	}
	if u.Host != "" && !sameEndpoint(u, upstreamURL) {
		return v
	}
	u.Scheme, u.Host = "", ""
	u.Path = alias.clientPath(u.Path)
	return v[:start+1] + u.String() + v[end:]
}

// sameEndpoint 判断 u 是否指向上游自身：scheme 相同、主机名忽略大小写后相同，
// 省略的端口按 scheme 补为默认端口，registry.example.com 与 registry.example.com:443 视为同一地址
func sameEndpoint(u, upstreamURL *url.URL) bool {
	return strings.EqualFold(u.Scheme, upstreamURL.Scheme) &&
		strings.EqualFold(u.Hostname(), upstreamURL.Hostname()) &&
		portOrDefault(u) == portOrDefault(upstreamURL)
}

func portOrDefault(u *url.URL) string {
	if p := u.Port(); p != "" {
		return p
	}
	switch strings.ToLower(u.Scheme) {
	case "https":
		return "443"
	case "http":
		return "80"
	}
	return ""
}
