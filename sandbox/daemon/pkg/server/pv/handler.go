package pv

import (
	"errors"
	"io"

	"github.com/gin-gonic/gin"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

// bindJSON 绑定并校验请求体, 复用 fs/process 包一致的空 body 处理。
// 绑定失败时已写入响应, 返回 false, 调用方直接 return。
func bindJSON(c *gin.Context, req any) bool {
	if err := c.ShouldBindJSON(req); err != nil {
		if errors.Is(err, io.EOF) {
			httputil.BadRequestResponse(c, errors.New("request body is empty or missing"))
		} else {
			httputil.BadRequestResponse(c, err)
		}
		return false
	}
	return true
}

// resolveJailed 依次做两道路径校验, 逃逸时以 403 结束请求。
// 返回的 full 为 jail 内绝对路径(未解析 symlink), jailRoot 供 handler 内二次校验用。
func resolveJailed(c *gin.Context, rootDir, basePath, relPath string) (full, jailRoot string, ok bool) {
	full, jailRoot, err := Resolve(rootDir, basePath, relPath)
	if err != nil {
		httputil.ForbiddenResponse(c, err)
		return "", "", false
	}
	return full, jailRoot, true
}
