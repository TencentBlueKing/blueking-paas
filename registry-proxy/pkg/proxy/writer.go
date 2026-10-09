package proxy

import (
	"net/http"
	"net/textproto"
	"net/url"
	"strings"
)

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
func sanitizeUpstreamHeaders(h http.Header, st *reqState) {
	// 逐跳头只对代理与上游之间的连接有效；HTTP/2 客户端收到 Connection、Keep-Alive 等头会判定为协议错误
	removeHopHeaders(h)
	// 上游质询指向上游 token 服务，透传会诱导客户端绕过代理；上游 Cookie 可能是代理账号的会话
	h.Del("WWW-Authenticate")
	h.Del("Set-Cookie")
	if links := h.Values("Link"); len(links) > 0 {
		out := make([]string, len(links))
		for i, l := range links {
			out[i] = rewriteLink(l, st.upstream.URL, st.upstream.Alias+"/")
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

// rewriteLink 把 Link 头（tags/list 分页）中指向上游 /v2/<repo> 的地址改写为代理的相对地址
func rewriteLink(v string, upstreamURL *url.URL, prefix string) string {
	start := strings.Index(v, "<")
	end := strings.Index(v, ">")
	if start < 0 || end < start {
		return v
	}
	u, err := url.Parse(v[start+1 : end])
	if err != nil || !strings.HasPrefix(u.Path, "/v2/") {
		return v
	}
	if u.Host != "" && !strings.EqualFold(u.Host, upstreamURL.Host) {
		return v
	}
	u.Scheme, u.Host = "", ""
	u.Path = "/v2/" + prefix + strings.TrimPrefix(u.Path, "/v2/")
	return v[:start+1] + u.String() + v[end:]
}
