package proxy

import (
	"encoding/json"
	"io"
	"sync"
)

// AuditEntry 是一条审计记录，所有字段都必须输出
type AuditEntry struct {
	TS           string `json:"ts"`
	Sub          string `json:"sub"`
	JTI          string `json:"jti"`
	AppCode      string `json:"app_code"`
	Module       string `json:"module"`
	RemoteAddr   string `json:"remote_addr"`
	Method       string `json:"method"`
	Route        string `json:"route"`
	Repo         string `json:"repo"`
	Upstream     string `json:"upstream"`
	Reference    string `json:"reference"`
	Status       int    `json:"status"`
	ReqBytes     int64  `json:"req_bytes"`
	RespBytes    int64  `json:"resp_bytes"`
	Ms           int64  `json:"ms"`
	RedirectHost string `json:"redirect_host"`
	Deny         string `json:"deny"`
}

// JSONAuditor 把审计记录按行输出为 JSON。写入失败不阻断请求，通过 OnError 通知调用方。
type JSONAuditor struct {
	mu      sync.Mutex
	w       io.Writer
	OnError func(error)
}

func NewJSONAuditor(w io.Writer) *JSONAuditor { return &JSONAuditor{w: w} }

func (a *JSONAuditor) Audit(e AuditEntry) {
	b, err := json.Marshal(e)
	if err == nil {
		a.mu.Lock()
		_, err = a.w.Write(append(b, '\n'))
		a.mu.Unlock()
	}
	if err != nil && a.OnError != nil {
		a.OnError(err)
	}
}
