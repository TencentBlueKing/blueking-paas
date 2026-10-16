package proxy

import (
	"context"
	"io"
	"net/http"
	"time"
)

const maxDrainBytes = 64 << 10

// forwardedRequestHeaders 是转发给上游的客户端请求头。只放行 OCI 客户端需要的头，
// 客户端的 Authorization、Cookie 与逐跳头都不会到达上游。
var forwardedRequestHeaders = []string{
	"Accept", "Accept-Encoding", "Content-Type", "Content-Range", "Range",
	"If-Match", "If-None-Match", "If-Modified-Since", "If-Range", "User-Agent",
}

// upstreamHeader 构造发往上游的请求头：代理换取的 Authorization 加上白名单内的客户端请求头
func upstreamHeader(r *http.Request, auth string) http.Header {
	header := http.Header{}
	if auth != "" {
		header.Set("Authorization", auth)
	}
	for _, k := range forwardedRequestHeaders {
		if v := r.Header.Values(k); len(v) > 0 {
			header[k] = v
		}
	}
	if r.ContentLength != 0 {
		// 上游在读取请求体前就拒绝时（如鉴权失败），避免白白上传 GB 级的数据
		header.Set("Expect", "100-continue")
	}
	return header
}

// upstreamAuthorization 按转发计划的 scope 换取上游 Authorization 头的值，匿名访问时为空。
// 失败时的拒绝原因由 upstream.ReasonOf 从返回的错误中取得。
func (s *Server) upstreamAuthorization(ctx context.Context, plan *forwardPlan) (string, error) {
	up := plan.upstream
	value, hit, err := up.Auth.Header(ctx, plan.scopes)
	switch {
	case err != nil:
		s.metrics.upstreamAuth.WithLabelValues(up.Alias, "error").Inc()
		return "", err
	case hit:
		s.metrics.upstreamAuth.WithLabelValues(up.Alias, "hit").Inc()
	default:
		s.metrics.upstreamAuth.WithLabelValues(up.Alias, "miss").Inc()
	}
	return value, nil
}

// send 向上游发送请求，不跟随重定向。上游返回 401 时作废对应的 Authorization 缓存；
// 无请求体的请求重新鉴权后重试一次，有请求体的请求无法重放，由下一个请求重新鉴权。
// 仍为 401 的响应原样返回，由调用方改为 502。
func (s *Server) send(r *http.Request, plan *forwardPlan, header http.Header) (*http.Response, error) {
	up := plan.upstream
	req, err := http.NewRequestWithContext(r.Context(), r.Method, plan.target.String(), nil)
	if err != nil {
		return nil, err
	}
	req.Header = header
	if r.ContentLength != 0 {
		// 流式转发客户端请求体，并保留其声明的长度，避免被改为 chunked 编码上传
		req.Body, req.ContentLength = r.Body, r.ContentLength
	}

	start := time.Now()
	resp, err := up.Transport.RoundTrip(req)
	if err == nil && resp.StatusCode == http.StatusUnauthorized {
		up.Auth.Invalidate(plan.scopes)
		s.metrics.upstreamAuth.WithLabelValues(up.Alias, "invalidated").Inc()
		if r.ContentLength == 0 {
			resp, err = s.retry(req, resp, plan)
		}
	}
	s.metrics.upstreamDuration.WithLabelValues(up.Alias, plan.route.Kind).Observe(time.Since(start).Seconds())
	return resp, err
}

// retry 在上游提前作废 token 时重新鉴权并重放一次无请求体的请求
func (s *Server) retry(prev *http.Request, resp *http.Response, plan *forwardPlan) (*http.Response, error) {
	_, _ = io.Copy(io.Discard, io.LimitReader(resp.Body, maxDrainBytes))
	_ = resp.Body.Close()

	auth, err := s.upstreamAuthorization(prev.Context(), plan)
	if err != nil {
		return nil, err
	}
	again := prev.Clone(prev.Context())
	if auth != "" {
		again.Header.Set("Authorization", auth)
	} else {
		again.Header.Del("Authorization")
	}
	resp, err = plan.upstream.Transport.RoundTrip(again)
	if err == nil && resp.StatusCode == http.StatusUnauthorized {
		plan.upstream.Auth.Invalidate(plan.scopes)
	}
	return resp, err
}
