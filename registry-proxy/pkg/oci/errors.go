package oci

import (
	"encoding/json"
	"net/http"
)

// DenyReason 是拒绝原因。空串表示放行。取值同时用于错误响应消息与审计日志 deny 字段。
type DenyReason string

const (
	DenyTokenMissing      DenyReason = "token_missing"
	DenyTokenExpired      DenyReason = "token_expired"
	DenyTokenInvalid      DenyReason = "token_invalid"
	DenyInvalidQuery      DenyReason = "invalid_query"
	DenyRouteNotFound     DenyReason = "route_not_found"
	DenyDeleteNotAllowed  DenyReason = "delete_not_allowed"
	DenyUnknownUpstream   DenyReason = "unknown_upstream"
	DenyPushNotGranted    DenyReason = "push_not_granted"
	DenyTagNotGranted     DenyReason = "tag_not_granted"
	DenyPullDenied        DenyReason = "pull_denied"
	DenyPullNotGranted    DenyReason = "pull_not_granted"
	DenyUploadSession     DenyReason = "invalid_upload_session"
	DenyUpstreamAuth      DenyReason = "upstream_auth_failed"
	DenyUpstreamUnreached DenyReason = "upstream_unreachable"
	// DenyInternal 为代理自身的内部错误，不对外作为业务拒绝原因，仅用于排障
	DenyInternal DenyReason = "internal_error"
)

// MessagePrefix 是代理自身错误的固定标记，apiserver 据此把构建失败归类为「镜像凭证不可用」
const MessagePrefix = "bkpaas-registry-proxy: "

// Challenge 是 401 响应携带的质询，引导客户端以 Basic 方式带上构建 token
const Challenge = `Basic realm="bkpaas-registry-proxy"`

// APIVersionHeader 是 Docker Registry v2 的版本头
const APIVersionHeader = "Docker-Distribution-API-Version"

type errorBody struct {
	Errors []errorItem `json:"errors"`
}

type errorItem struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}

func errorCode(status int) string {
	switch status {
	case http.StatusUnauthorized:
		return "UNAUTHORIZED"
	case http.StatusForbidden:
		return "DENIED"
	case http.StatusNotFound:
		return "UNSUPPORTED"
	default:
		return "UNKNOWN"
	}
}

// WriteError 按 OCI Distribution 错误格式输出代理自身产生的错误。
// 只有 401 带质询；HEAD 请求没有响应体。
func WriteError(w http.ResponseWriter, r *http.Request, status int, deny DenyReason) {
	h := w.Header()
	for k := range h {
		delete(h, k)
	}
	h.Set("Content-Type", "application/json")
	h.Set(APIVersionHeader, "registry/2.0")
	if status == http.StatusUnauthorized {
		h.Set("WWW-Authenticate", Challenge)
	}
	body, _ := json.Marshal(errorBody{Errors: []errorItem{{Code: errorCode(status), Message: MessagePrefix + string(deny)}}})
	w.WriteHeader(status)
	if r.Method != http.MethodHead {
		_, _ = w.Write(body)
	}
}
