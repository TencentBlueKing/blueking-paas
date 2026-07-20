package volumefs

import (
	"errors"
	"io"
	"os"

	"github.com/gin-gonic/gin"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

// bindJSON 绑定并校验 JSON body, 空 body 转 400。失败时已写响应, 返回 false。
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

// bindQuery 绑定并校验 query 参数。失败时已写响应, 返回 false。
func bindQuery(c *gin.Context, req any) bool {
	if err := c.ShouldBindQuery(req); err != nil {
		httputil.BadRequestResponse(c, err)
		return false
	}
	return true
}

// resolveJailed 做 jail 前缀校验, 逃逸时以 403 结束。full 为 jail 内绝对路径(未解析 symlink)。
func resolveJailed(c *gin.Context, rootDir, basePath, relPath string) (full, jailRoot string, ok bool) {
	full, jailRoot, err := Resolve(rootDir, basePath, relPath)
	if err != nil {
		httputil.ForbiddenResponse(c, err)
		return "", "", false
	}
	return full, jailRoot, true
}

// respondErr 把 jail/文件系统错误映射到对应的 HTTP 状态码。
func respondErr(c *gin.Context, err error) {
	switch {
	case errors.Is(err, ErrPathEscape), errors.Is(err, os.ErrPermission):
		httputil.ForbiddenResponse(c, err)
	case errors.Is(err, os.ErrNotExist):
		httputil.NotFoundResponse(c, err)
	default:
		httputil.InternalErrorResponse(c, err)
	}
}
