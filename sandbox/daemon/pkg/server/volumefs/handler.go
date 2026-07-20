package volumefs

import (
	"errors"
	"io"
	"os"
	"strings"

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

// openJailedRoot opens the volume jail and validates a root-relative path.
// os.Root performs the authoritative traversal and symlink checks for operations.
func openJailedRoot(c *gin.Context, rootDir, basePath, relPath string) (root *os.Root, name string, ok bool) {
	name, err := validateRootPath(relPath)
	if err != nil {
		httputil.ForbiddenResponse(c, err)
		return nil, "", false
	}
	root, err = openVolumeRoot(rootDir, basePath)
	if err != nil {
		httputil.ForbiddenResponse(c, err)
		return nil, "", false
	}
	return root, name, true
}

// respondErr 把 jail/文件系统错误映射到对应的 HTTP 状态码。
func respondErr(c *gin.Context, err error) {
	switch {
	case errors.Is(err, ErrPathEscape), errors.Is(err, os.ErrPermission), strings.Contains(err.Error(), "path escapes"):
		httputil.ForbiddenResponse(c, err)
	case errors.Is(err, os.ErrNotExist):
		httputil.NotFoundResponse(c, err)
	default:
		httputil.InternalErrorResponse(c, err)
	}
}
