package proxy

import (
	"io"
	"net/http"
	"net/url"
	"time"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/oci"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/upstream"
)

const maxDrainBytes = 64 << 10

// send 向上游发送请求，不跟随重定向。上游返回 401 时作废对应的 Authorization 缓存；
// 无请求体的请求重新鉴权后重试一次，有请求体的请求无法重放，由下一个请求重新鉴权。
func (s *Server) send(r *http.Request, st *reqState, target *url.URL, header http.Header) (*http.Response, error) {
	up := st.upstream
	req, err := http.NewRequestWithContext(r.Context(), r.Method, target.String(), nil)
	if err != nil {
		return nil, err
	}
	req.Header = header
	if st.clientBodyLen != 0 {
		// 流式转发客户端请求体，并保留其声明的长度，避免被改为 chunked 编码上传
		req.Body, req.ContentLength = r.Body, st.clientBodyLen
	}

	start := time.Now()
	resp, err := up.Transport.RoundTrip(req)
	if err == nil && resp.StatusCode == http.StatusUnauthorized {
		up.Invalidate(st.scopes)
		s.metrics.upstreamAuth.WithLabelValues(up.Alias, "invalidated").Inc()
		if st.clientBodyLen == 0 {
			resp, err = s.retry(req, resp, up, st)
		}
	}
	s.metrics.upstreamDuration.WithLabelValues(up.Alias, st.route.Kind).Observe(time.Since(start).Seconds())
	return resp, err
}

// retry 在上游提前作废 token 时重新鉴权并重放一次无请求体的请求
func (s *Server) retry(prev *http.Request, resp *http.Response, up *upstream.Upstream, st *reqState) (*http.Response, error) {
	_, _ = io.Copy(io.Discard, io.LimitReader(resp.Body, maxDrainBytes))
	_ = resp.Body.Close()

	value, _, err := up.Authorization(prev.Context(), st.scopes)
	if err != nil {
		st.deny = upstream.ReasonOf(err)
		s.metrics.upstreamAuth.WithLabelValues(up.Alias, "error").Inc()
		return nil, err
	}
	s.metrics.upstreamAuth.WithLabelValues(up.Alias, "miss").Inc()
	again := prev.Clone(prev.Context())
	if value != "" {
		again.Header.Set("Authorization", value)
	} else {
		again.Header.Del("Authorization")
	}
	resp, err = up.Transport.RoundTrip(again)
	if err == nil && resp.StatusCode == http.StatusUnauthorized {
		up.Invalidate(st.scopes)
		st.deny = oci.DenyUpstreamAuth
	}
	return resp, err
}
