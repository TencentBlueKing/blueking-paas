package proxy

import (
	"net/http"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
)

const namespace = "bkpaas_registry_proxy"

// Metrics 是代理的 Prometheus 指标。标签取值均有界：路由、方法、状态码、上游别名、拒绝原因。
type Metrics struct {
	requests         *prometheus.CounterVec
	requestDuration  *prometheus.HistogramVec
	upstreamDuration *prometheus.HistogramVec
	transferred      *prometheus.CounterVec
	upstreamAuth     *prometheus.CounterVec
	denied           *prometheus.CounterVec
	auditFailures    prometheus.Counter
}

// NewMetrics 创建并注册指标，reg 为 nil 时只创建不注册（用于测试）
func NewMetrics(reg prometheus.Registerer) *Metrics {
	m := &Metrics{
		requests: prometheus.NewCounterVec(prometheus.CounterOpts{
			Namespace: namespace, Name: "requests_total",
			Help: "Requests handled by the proxy, by route, method and response status code.",
		}, []string{"route", "method", "code"}),
		requestDuration: prometheus.NewHistogramVec(prometheus.HistogramOpts{
			Namespace: namespace, Name: "request_duration_seconds",
			Help:    "Time from receiving a request to finishing its response, including body transfer.",
			Buckets: []float64{.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10, 30, 60, 300},
		}, []string{"route"}),
		upstreamDuration: prometheus.NewHistogramVec(prometheus.HistogramOpts{
			Namespace: namespace, Name: "upstream_request_duration_seconds",
			Help:    "Time until upstream response headers are received (including request body upload).",
			Buckets: []float64{.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10, 30, 60, 300},
		}, []string{"upstream", "route"}),
		transferred: prometheus.NewCounterVec(prometheus.CounterOpts{
			Namespace: namespace, Name: "transferred_bytes_total",
			Help: "Body bytes forwarded through the proxy; direction is request (client to upstream) or response.",
		}, []string{"upstream", "direction"}),
		upstreamAuth: prometheus.NewCounterVec(prometheus.CounterOpts{
			Namespace: namespace, Name: "upstream_auth_total",
			Help: "Upstream Authorization lookups by result: hit, miss, error, invalidated.",
		}, []string{"upstream", "result"}),
		denied: prometheus.NewCounterVec(prometheus.CounterOpts{
			Namespace: namespace, Name: "denied_total",
			Help: "Requests rejected by the proxy, by deny reason.",
		}, []string{"deny"}),
		auditFailures: prometheus.NewCounter(prometheus.CounterOpts{
			Namespace: namespace, Name: "audit_write_failures_total",
			Help: "Audit records that failed to be written.",
		}),
	}
	if reg != nil {
		reg.MustRegister(m.requests, m.requestDuration, m.upstreamDuration, m.transferred,
			m.upstreamAuth, m.denied, m.auditFailures)
	}
	return m
}

// AuditFailed 记录一次审计写入失败
func (m *Metrics) AuditFailed() { m.auditFailures.Inc() }

func (m *Metrics) observeRequest(route, method string, status int, d time.Duration) {
	m.requests.WithLabelValues(route, methodLabel(method), strconv.Itoa(status)).Inc()
	m.requestDuration.WithLabelValues(route).Observe(d.Seconds())
}

func methodLabel(m string) string {
	switch m {
	case http.MethodGet, http.MethodHead, http.MethodPost, http.MethodPut, http.MethodPatch, http.MethodDelete:
		return m
	default:
		return "OTHER"
	}
}
