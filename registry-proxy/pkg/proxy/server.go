// Package proxy 实现镜像代理的协议转发层：接收构建容器的 OCI Distribution v2 请求，
// 经鉴权、授权钩子判定后，用代理自身持有的上游凭证转发给真实仓库。
package proxy

import (
	"errors"
	"io"
	"log/slog"
	"net/http"
	"net/url"
	"time"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/oci"
	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/upstream"
)

// Options 是创建 Server 所需的依赖
type Options struct {
	// Upstreams 以别名为键，创建 Server 后不能再修改
	Upstreams     map[string]*upstream.Upstream
	Authenticator Authenticator
	Authorizer    Authorizer
	// Auditor 为空时不输出审计
	Auditor Auditor
	// UploadSessionKey 签名上传会话，多副本之间必须相同
	UploadSessionKey []byte
	// PreviousUploadSessionKey 为轮换前的密钥，只用于校验
	PreviousUploadSessionKey []byte
	// UploadSessionTTL 为上传会话有效期，缺省 1 小时
	UploadSessionTTL time.Duration
	Metrics          *Metrics
	Logger           *slog.Logger
}

// Server 是代理的 http.Handler
type Server struct {
	upstreams map[string]*upstream.Upstream
	authn     Authenticator
	authz     Authorizer
	auditor   Auditor
	metrics   *Metrics
	log       *slog.Logger
	sessions  *sessionCodec
	now       func() time.Time
}

// reqRecord 是一次请求的审计与指标记录，finish 对所有请求（包括最早被拒绝的）输出它在请求停下时的状态。
// 每个字段只写一次，且只由 ServeHTTP 与 handle 写入；各处理阶段不读它做判断。
type reqRecord struct {
	// start 与 route 在请求进入时写入，route 为路由解析结果
	start time.Time
	route oci.Route
	// identity 在认证通过后写入
	identity Identity
	// plan 在生成转发计划后写入，未进入转发阶段的请求为空；审计的路由与上游以它为准
	plan *forwardPlan
	// deny 为 handle 返回的拒绝原因，放行时为空
	deny oci.DenyReason
}

// New 创建代理
func New(opts Options) (*Server, error) {
	if len(opts.Upstreams) == 0 || opts.Authenticator == nil || opts.Authorizer == nil {
		return nil, errors.New("proxy: upstreams, authenticator and authorizer are required")
	}
	if len(opts.UploadSessionKey) == 0 {
		return nil, errors.New("proxy: upload session key is required")
	}
	s := &Server{
		upstreams: opts.Upstreams,
		authn:     opts.Authenticator,
		authz:     opts.Authorizer,
		auditor:   opts.Auditor,
		metrics:   opts.Metrics,
		log:       opts.Logger,
		now:       time.Now,
	}
	if s.metrics == nil {
		s.metrics = NewMetrics(nil)
	}
	if s.log == nil {
		s.log = slog.New(slog.DiscardHandler)
	}
	ttl := opts.UploadSessionTTL
	if ttl <= 0 {
		ttl = time.Hour
	}
	s.sessions = &sessionCodec{
		primary:  opts.UploadSessionKey,
		previous: opts.PreviousUploadSessionKey,
		ttl:      ttl,
		now:      func() time.Time { return s.now() },
	}
	return s, nil
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// query 为客户端查询串的唯一解析结果，路由解析、mount 降级与转发都只使用它，转发时重新编码
	query, queryErr := parseQuery(r.URL.RawQuery)
	if queryErr != nil {
		query = url.Values{}
	}
	rt := oci.ParseRoute(r.Method, r.URL.EscapedPath(), query)
	rec := &reqRecord{start: s.now(), route: rt}
	body := &countingBody{ReadCloser: r.Body}
	r.Body = body
	rw := &responseWriter{ResponseWriter: w}
	defer s.finish(rec, rw, body, r)
	if queryErr != nil {
		rec.deny = s.reject(rw, r, http.StatusBadRequest, oci.DenyInvalidQuery)
		return
	}
	rec.deny = s.handle(rw, r, rec, rt, query)
}

// handle 依次完成鉴权、/v2/ 探活、授权、纵深防御与转发计划的生成（客户端侧校验，失败返回 4xx），再交给 forward。
// 返回拒绝原因，放行时为空；只向 rec 写入 identity 与 plan。
func (s *Server) handle(
	w *responseWriter, r *http.Request, rec *reqRecord, route oci.Route, query url.Values,
) oci.DenyReason {
	p, deny := s.authn.Authenticate(r)
	if deny != "" {
		oci.WriteError(w, r, http.StatusUnauthorized, deny)
		// 未带 token 的 /v2/ 探活是客户端正常的质询流程，审计与指标中不记为拒绝
		if route.Kind == oci.RoutePing && deny == oci.DenyTokenMissing {
			return ""
		}
		return deny
	}
	rec.identity = p.Identity()

	if route.Kind == oci.RoutePing {
		if route.Action == "" {
			return s.reject(w, r, http.StatusNotFound, oci.DenyRouteNotFound)
		}
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set(oci.APIVersionHeader, "registry/2.0")
		w.WriteHeader(http.StatusOK)
		if r.Method != http.MethodHead {
			_, _ = w.Write([]byte("{}"))
		}
		return ""
	}

	d := s.authz.Authorize(p, r.Method, route)
	if d.Status != 0 {
		return s.reject(w, r, d.Status, d.Deny)
	}
	// 以下检查不依赖授权钩子的实现：DELETE、非法路由与未配置的上游（在 resolve 中）永远不转发
	switch {
	case r.Method == http.MethodDelete:
		return s.reject(w, r, http.StatusForbidden, oci.DenyDeleteNotAllowed)
	case !route.Valid():
		return s.reject(w, r, http.StatusNotFound, oci.DenyRouteNotFound)
	}

	plan, deny := s.resolve(r, route, query, d)
	if deny != "" {
		return s.reject(w, r, http.StatusForbidden, deny)
	}
	rec.plan = plan
	return s.forward(w, r, plan)
}

// forward 按转发计划请求上游，并把上游响应改写后流式返回给客户端。这一阶段的失败都返回 502。
// 返回拒绝原因，放行时为空。
func (s *Server) forward(w *responseWriter, r *http.Request, plan *forwardPlan) oci.DenyReason {
	up, kind := plan.upstream, plan.route.Kind
	auth, err := s.upstreamAuthorization(r.Context(), plan)
	if err != nil {
		s.log.Warn("upstream authorization failed", "upstream", up.Alias, "route", kind, "error", err)
		return s.reject(w, r, http.StatusBadGateway, upstream.ReasonOf(err))
	}

	resp, err := s.send(r, plan, upstreamHeader(r, auth))
	if err != nil {
		s.log.Warn("upstream request failed", "upstream", up.Alias, "route", kind, "method", r.Method, "error", err)
		return s.reject(w, r, http.StatusBadGateway, upstream.ReasonOf(err))
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.StatusCode == http.StatusUnauthorized {
		// 上游拒绝代理自身的凭证，改为 502，避免客户端误以为构建 token 无效
		s.log.Warn("upstream rejected proxy credentials", "upstream", up.Alias, "route", kind, "method", r.Method)
		return s.reject(w, r, http.StatusBadGateway, oci.DenyUpstreamAuth)
	}

	h := w.Header()
	for k, v := range resp.Header {
		h[k] = v
	}
	sanitizeUpstreamHeaders(h, plan)
	if err := s.rewriteLocation(h, r.Method, resp.StatusCode, plan); err != nil {
		s.log.Warn("unexpected upstream Location", "upstream", up.Alias, "route", kind, "error", err)
		return s.reject(w, r, http.StatusBadGateway, oci.DenyUpstreamUnreached)
	}
	w.WriteHeader(resp.StatusCode)
	if r.Method == http.MethodHead {
		return ""
	}
	buf := copyBufPool.Get().(*[]byte)
	defer copyBufPool.Put(buf)
	// 客户端或上游中途断开时 CopyBuffer 返回，上游响应体随即关闭；请求 context 取消后上游连接也会释放
	_, _ = io.CopyBuffer(w, resp.Body, *buf)
	return ""
}

// finish 在请求结束时更新指标并输出审计记录，包括被拒绝和未认证的请求
func (s *Server) finish(rec *reqRecord, rw *responseWriter, body *countingBody, r *http.Request) {
	status := rw.status
	if status == 0 {
		status = http.StatusOK
	}
	// 进入转发阶段的请求以 mount 降级后的路由记审计
	route := rec.route
	if rec.plan != nil {
		route = rec.plan.route
	}
	elapsed := s.now().Sub(rec.start)
	s.metrics.observeRequest(route.Kind, r.Method, status, elapsed)
	if rec.deny != "" {
		s.metrics.denied.WithLabelValues(string(rec.deny)).Inc()
	}
	if rec.plan != nil {
		alias := rec.plan.upstream.Alias
		s.metrics.transferred.WithLabelValues(alias, "request").Add(float64(body.n))
		s.metrics.transferred.WithLabelValues(alias, "response").Add(float64(rw.bytes))
	}
	if s.auditor == nil {
		return
	}
	e := AuditEntry{
		TS:         rec.start.UTC().Format(time.RFC3339Nano),
		Sub:        rec.identity.Subject,
		JTI:        rec.identity.TokenID,
		AppCode:    rec.identity.AppCode,
		Module:     rec.identity.Module,
		RemoteAddr: remoteIP(r.RemoteAddr),
		Method:     r.Method,
		Route:      route.Kind,
		Status:     status,
		ReqBytes:   body.n,
		RespBytes:  rw.bytes,
		Ms:         elapsed.Milliseconds(),
		Deny:       rec.deny,
	}
	if route.Kind != oci.RoutePing && route.Kind != oci.RouteUnknown {
		e.Repo, e.Upstream, e.Reference = route.Repo, route.Upstream, route.Reference
	}
	if status == http.StatusTemporaryRedirect || status == http.StatusPermanentRedirect {
		if u, err := url.Parse(rw.Header().Get("Location")); err == nil {
			e.RedirectHost = u.Hostname()
		}
	}
	s.auditor.Audit(e)
}

// reject 写出 OCI 错误响应，并原样返回拒绝原因
func (s *Server) reject(w http.ResponseWriter, r *http.Request, status int, deny oci.DenyReason) oci.DenyReason {
	oci.WriteError(w, r, status, deny)
	return deny
}
