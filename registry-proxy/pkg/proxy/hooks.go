package proxy

import (
	"net/http"

	"github.com/TencentBlueking/blueking-paas/registry-proxy/pkg/oci"
)

// Identity 是已认证请求的身份，写入审计日志
type Identity struct {
	// Subject 为构建 ID：应用构建为 BuildProcess ID，沙箱镜像构建为 ImageBuildRecord ID
	Subject string
	// TokenID 为构建 token 的 jti
	TokenID string
	AppCode string
	// Module 仅应用构建携带，沙箱镜像构建为空
	Module string
}

// Principal 是鉴权钩子的输出，原样交给授权钩子
type Principal interface {
	Identity() Identity
}

// Authenticator 是 token 鉴权钩子。deny 非空表示认证失败，取值为 token_missing / token_invalid / token_expired。
type Authenticator interface {
	Authenticate(r *http.Request) (p Principal, deny oci.DenyReason)
}

// Decision 是授权钩子的判定。
type Decision struct {
	// Status 是拒绝时的 HTTP 状态码，取 401、403 或 404。0 表示放行。
	Status int
	// Deny 为空表示放行
	Deny oci.DenyReason
	// DropMount 为 true 时去掉 mount/from 参数，把跨仓库挂载降级为普通上传
	DropMount bool
}

// Authorizer 是授权判定钩子，在转发之前执行；被拒绝的请求不会到达上游
type Authorizer interface {
	Authorize(p Principal, method string, rt oci.Route) Decision
}

// Auditor 接收每个请求的审计记录，包括未认证的请求
type Auditor interface {
	Audit(e AuditEntry)
}
