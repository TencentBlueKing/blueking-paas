// Package proxy 实现镜像代理的协议转发层：接收构建容器的 OCI Distribution v2 请求，
// 经鉴权、授权钩子判定后，用代理自身持有的上游凭证转发给真实仓库。
package proxy

import (
	"errors"
	"io"
	"log/slog"
	"net"
	"net/http"
	"net/url"
	"strings"
	"sync"
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

// reqState 贯穿一次请求的处理过程
type reqState struct {
	start    time.Time
	route    oci.Route
	identity Identity
	upstream *upstream.Upstream
	// session 为本次请求续传的上传会话，非续传请求为空
	session *uploadSession
	// scopes 为本次请求换取上游 Authorization 使用的 scope，上游返回 401 时据此作废缓存
	scopes []upstream.Scope
	// clientBodyLen 为客户端请求体长度：0 表示无请求体，-1 表示长度未知
	clientBodyLen int64
	// deny 为拒绝原因，放行时为空
	deny string
}

// forwardedRequestHeaders 是转发给上游的客户端请求头。只放行 OCI 客户端需要的头，
// 客户端的 Authorization、Cookie 与逐跳头都不会到达上游。
var forwardedRequestHeaders = []string{
	"Accept", "Accept-Encoding", "Content-Type", "Content-Range", "Range",
	"If-Match", "If-None-Match", "If-Modified-Since", "If-Range", "User-Agent",
}

var copyBufPool = sync.Pool{New: func() any { b := make([]byte, 64<<10); return &b }}

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
	st := &reqState{
		start:         s.now(),
		route:         oci.ParseRoute(r.Method, r.URL.EscapedPath(), r.URL.Query()),
		clientBodyLen: r.ContentLength,
	}
	body := &countingBody{ReadCloser: r.Body}
	r.Body = body
	rw := &responseWriter{ResponseWriter: w}
	defer s.finish(st, rw, body, r)
	s.handle(rw, r, st)
}

func (s *Server) handle(w *responseWriter, r *http.Request, st *reqState) {
	p, deny := s.authn.Authenticate(r)
	if deny != "" {
		// 未带 token 的 /v2/ 探活是客户端正常的质询流程，审计中不记为拒绝
		// (reqState deny 会在 finish 中被计入 metrics)
		if st.route.Kind != oci.RoutePing || deny != oci.DenyTokenMissing {
			st.deny = deny
		}
		oci.WriteError(w, r, http.StatusUnauthorized, deny)
		return
	}
	st.identity = p.Identity()

	if st.route.Kind == oci.RoutePing {
		if st.route.Action == "" {
			s.reject(w, r, st, http.StatusNotFound, oci.DenyRouteNotFound)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set(oci.APIVersionHeader, "registry/2.0")
		w.WriteHeader(http.StatusOK)
		if r.Method != http.MethodHead {
			_, _ = w.Write([]byte("{}"))
		}
		return
	}

	d := s.authz.Authorize(p, r.Method, st.route)
	if d.Status != 0 {
		s.reject(w, r, st, d.Status, d.Deny)
		return
	}
	// 以下检查不依赖授权钩子的实现：DELETE、非法路由与未配置的上游永远不转发
	switch {
	case r.Method == http.MethodDelete:
		s.reject(w, r, st, http.StatusForbidden, oci.DenyDeleteNotAllowed)
		return
	case !st.route.Valid():
		s.reject(w, r, st, http.StatusNotFound, oci.DenyRouteNotFound)
		return
	}
	up, ok := s.upstreams[st.route.Upstream]
	if !ok {
		s.reject(w, r, st, http.StatusForbidden, oci.DenyUnknownUpstream)
		return
	}
	st.upstream = up

	// 客户端把所有上游视为同一个 registry，会尝试跨上游挂载；直接转发会让上游按同名路径查找来源仓库。
	// 缺少 from 的 mount 在部分 registry 上表示「从凭证可读的任意仓库挂载」，而代理的上游账号可读全平台。
	// 以上情况以及来源不可读时，都去掉 mount / from，降级为普通上传。
	if query := r.URL.Query(); st.route.Kind == oci.RouteUpload &&
		!st.route.Session && (query.Has("mount") || query.Has("from")) {
		from := st.route.MountFrom
		if from == "" || !query.Has("mount") || d.DropMount || oci.UpstreamOf(from) != up.Alias {
			query.Del("mount")
			query.Del("from")
			st.route.MountFrom = ""
		} else {
			query.Set("from", strings.TrimPrefix(from, up.Alias+"/"))
		}
		r.URL.RawQuery = query.Encode()
	}

	s.forward(w, r, st)
}

func (s *Server) reject(w http.ResponseWriter, r *http.Request, st *reqState, status int, deny string) {
	st.deny = deny
	oci.WriteError(w, r, status, deny)
}

// forward 把已授权的请求转发给上游，并把上游响应改写后流式返回给客户端
func (s *Server) forward(w *responseWriter, r *http.Request, st *reqState) {
	up := st.upstream
	target, err := s.upstreamURL(r, st)
	if err != nil {
		s.reject(w, r, st, http.StatusForbidden, oci.DenyUploadSession)
		return
	}

	header, err := s.upstreamAuthorization(r, st)
	if err != nil {
		s.reject(w, r, st, http.StatusBadGateway, st.deny)
		return
	}
	for _, k := range forwardedRequestHeaders {
		if v := r.Header.Values(k); len(v) > 0 {
			header[k] = v
		}
	}
	if st.clientBodyLen != 0 {
		// 上游在读取请求体前就拒绝时（如鉴权失败），避免白白上传 GB 级的数据
		header.Set("Expect", "100-continue")
	}

	resp, err := s.send(r, st, target, header)
	if err != nil {
		if st.deny == "" {
			st.deny = oci.DenyUpstreamUnreached
		}
		s.log.Warn("upstream request failed", "upstream", up.Alias, "route", st.route.Kind, "method", r.Method, "error", err)
		s.reject(w, r, st, http.StatusBadGateway, st.deny)
		return
	}
	defer func() { _ = resp.Body.Close() }()
	if resp.StatusCode == http.StatusUnauthorized {
		// 上游拒绝代理自身的凭证，改为 502，避免客户端误以为构建 token 无效
		s.log.Warn("upstream rejected proxy credentials", "upstream", up.Alias, "route", st.route.Kind, "method", r.Method)
		s.reject(w, r, st, http.StatusBadGateway, oci.DenyUpstreamAuth)
		return
	}

	h := w.Header()
	for k, v := range resp.Header {
		h[k] = v
	}
	sanitizeUpstreamHeaders(h, st)
	if err := s.rewriteLocation(h, r.Method, resp.StatusCode, target, st); err != nil {
		s.log.Warn("unexpected upstream Location", "upstream", up.Alias, "route", st.route.Kind, "error", err)
		s.reject(w, r, st, http.StatusBadGateway, oci.DenyUpstreamUnreached)
		return
	}
	w.WriteHeader(resp.StatusCode)
	if r.Method == http.MethodHead {
		return
	}
	buf := copyBufPool.Get().(*[]byte)
	defer copyBufPool.Put(buf)
	// 客户端或上游中途断开时 CopyBuffer 返回，上游响应体随即关闭；请求 context 取消后上游连接也会释放
	_, _ = io.CopyBuffer(w, resp.Body, *buf)
}

// upstreamURL 计算上游地址：续传请求使用会话中记录的上游地址，其余请求去掉路径中的别名段
func (s *Server) upstreamURL(r *http.Request, st *reqState) (*url.URL, error) {
	target := *st.upstream.URL
	if !st.route.Session {
		target.Path = "/v2/" + strings.TrimPrefix(r.URL.Path, "/v2/"+st.upstream.Alias+"/")
		target.RawQuery = r.URL.RawQuery
		return &target, nil
	}

	sess, err := s.sessions.verify(st.route.SessionID, st.route.Repo)
	if err != nil {
		return nil, err
	}
	st.session = &sess
	loc, err := url.Parse(sess.Location)
	if err != nil {
		return nil, errInvalidSession
	}
	target.Path, target.RawPath, target.RawQuery = loc.Path, loc.RawPath, loc.RawQuery
	// 客户端只需要提供完成上传时的 digest，其余参数（如 _state）以上游返回的为准
	if d := r.URL.Query().Get("digest"); d != "" {
		q := target.Query()
		q.Set("digest", d)
		target.RawQuery = q.Encode()
	}
	return &target, nil
}

// upstreamAuthorization 按代理计算的 scope 换取上游 Authorization，返回只含该头的请求头
func (s *Server) upstreamAuthorization(r *http.Request, st *reqState) (http.Header, error) {
	up := st.upstream
	prefix := up.Alias + "/"
	// 上游 token 的 scope 是协议里的字符串，与路由动作类型分开
	actions := []string{string(oci.ActionPull)}
	if st.route.Action == oci.ActionPush {
		actions = append(actions, string(oci.ActionPush))
	}
	st.scopes = []upstream.Scope{{Repo: strings.TrimPrefix(st.route.Repo, prefix), Actions: actions}}
	if st.route.MountFrom != "" {
		st.scopes = append(st.scopes, upstream.Scope{Repo: strings.TrimPrefix(st.route.MountFrom, prefix), Actions: []string{string(oci.ActionPull)}})
	}

	value, hit, err := up.Authorization(r.Context(), st.scopes)
	switch {
	case err != nil:
		st.deny = upstream.ReasonOf(err)
		s.metrics.upstreamAuth.WithLabelValues(up.Alias, "error").Inc()
		s.log.Warn("upstream authorization failed", "upstream", up.Alias, "route", st.route.Kind, "error", err)
		return nil, err
	case hit:
		s.metrics.upstreamAuth.WithLabelValues(up.Alias, "hit").Inc()
	default:
		s.metrics.upstreamAuth.WithLabelValues(up.Alias, "miss").Inc()
	}
	header := http.Header{}
	if value != "" {
		header.Set("Authorization", value)
	}
	return header, nil
}

// rewriteLocation 改写上游响应的 Location：
//   - 上传会话（开始上传、续传、查询进度）的地址签名为会话 token，不向客户端暴露上游的上传状态；
//   - 指向上游 /v2/ 的地址改写为代理的相对地址，并补回别名段；
//   - 指向其他主机的地址（如 307 到对象存储的预签名地址）原样保留。
func (s *Server) rewriteLocation(h http.Header, method string, status int, target *url.URL, st *reqState) error {
	raw := h.Get("Location")
	if raw == "" {
		return nil
	}
	loc, err := target.Parse(raw)
	if err != nil {
		return err
	}
	up := st.upstream
	sameEndpoint := strings.EqualFold(loc.Scheme, up.URL.Scheme) && strings.EqualFold(loc.Host, up.URL.Host)

	if isUploadSessionResponse(st.route, method, status) {
		if !sameEndpoint {
			return errors.New("upload session Location on a foreign host " + loc.Host)
		}
		sess := uploadSession{Repo: st.route.Repo, Location: loc.RequestURI()}
		if st.session != nil {
			sess.Expiry = st.session.Expiry
		}
		token, err := s.sessions.sign(sess)
		if err != nil {
			return err
		}
		h.Set("Location", "/v2/"+st.route.Repo+"/blobs/uploads/"+token)
		return nil
	}

	if sameEndpoint && strings.HasPrefix(loc.Path, "/v2/") {
		rel := url.URL{Path: "/v2/" + up.Alias + "/" + strings.TrimPrefix(loc.Path, "/v2/"), RawQuery: loc.RawQuery}
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

func (s *Server) finish(st *reqState, rw *responseWriter, body *countingBody, r *http.Request) {
	status := rw.status
	if status == 0 {
		status = http.StatusOK
	}
	elapsed := s.now().Sub(st.start)
	s.metrics.observeRequest(st.route.Kind, r.Method, status, elapsed)
	if st.deny != "" {
		s.metrics.denied.WithLabelValues(st.deny).Inc()
	}
	if st.upstream != nil {
		s.metrics.transferred.WithLabelValues(st.upstream.Alias, "request").Add(float64(body.n))
		s.metrics.transferred.WithLabelValues(st.upstream.Alias, "response").Add(float64(rw.bytes))
	}
	if s.auditor == nil {
		return
	}
	e := AuditEntry{
		TS:         st.start.UTC().Format(time.RFC3339Nano),
		Sub:        st.identity.Subject,
		JTI:        st.identity.TokenID,
		AppCode:    st.identity.AppCode,
		Module:     st.identity.Module,
		RemoteAddr: remoteIP(r.RemoteAddr),
		Method:     r.Method,
		Route:      st.route.Kind,
		Status:     status,
		ReqBytes:   body.n,
		RespBytes:  rw.bytes,
		Ms:         elapsed.Milliseconds(),
		Deny:       st.deny,
	}
	if st.route.Kind != oci.RoutePing && st.route.Kind != oci.RouteUnknown {
		e.Repo, e.Upstream, e.Reference = st.route.Repo, st.route.Upstream, st.route.Reference
	}
	if status == http.StatusTemporaryRedirect || status == http.StatusPermanentRedirect {
		if u, err := url.Parse(rw.Header().Get("Location")); err == nil {
			e.RedirectHost = u.Hostname()
		}
	}
	s.auditor.Audit(e)
}

func remoteIP(addr string) string {
	host, _, err := net.SplitHostPort(addr)
	if err != nil {
		return addr
	}
	return host
}

type countingBody struct {
	io.ReadCloser
	n int64
}

func (b *countingBody) Read(p []byte) (int, error) {
	n, err := b.ReadCloser.Read(p)
	b.n += int64(n)
	return n, err
}
