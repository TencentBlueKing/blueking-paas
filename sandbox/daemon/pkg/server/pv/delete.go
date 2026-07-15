package pv

import (
	"errors"
	"os"

	"github.com/gin-gonic/gin"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/config"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

// DeleteFile godoc
//
//	@Summary		Delete a single file in a volume
//	@Description	Delete base_path/rel_path; deleting a non-existent file is idempotent
//	@Tags			pv
//	@Accept			json
//	@Produce		json
//	@Param			base_path	query		string	true	"jail root path issued by apiserver"
//	@Param			rel_path	query		string	true	"volume-relative path"
//	@Success		200			{object}	DeleteResponse
//	@Router			/files/cfs [delete]
//
//	@id				PVDeleteFile
func DeleteFile(c *gin.Context) {
	basePath := c.Query("base_path")
	relPath := c.Query("rel_path")
	if basePath == "" {
		httputil.BadRequestResponse(c, errors.New("base_path is required"))
		return
	}
	if relPath == "" {
		httputil.BadRequestResponse(c, errors.New("rel_path is required"))
		return
	}

	full, jailRoot, ok := resolveJailed(c, config.G.CFSRoot, basePath, relPath)
	if !ok {
		return
	}

	// symlink 兜底: 存在则二次校验真实路径; 不存在则视为已删除(幂等)
	real, err := ResolveSymlink(full, jailRoot)
	if err != nil {
		if os.IsNotExist(err) {
			httputil.SuccessResponse(c, DeleteResponse{Deleted: true})
			return
		}
		if errors.Is(err, ErrPathEscape) {
			httputil.ForbiddenResponse(c, err)
			return
		}
		httputil.InternalErrorResponse(c, err)
		return
	}

	// 仅支持删除单个文件, 拒绝目录(产物文件场景)
	info, err := os.Lstat(real)
	if err != nil {
		httputil.InternalErrorResponse(c, err)
		return
	}
	if info.IsDir() {
		httputil.BadRequestResponse(c, errors.New("cannot delete a directory"))
		return
	}

	if err := os.Remove(real); err != nil {
		if os.IsNotExist(err) {
			httputil.SuccessResponse(c, DeleteResponse{Deleted: true})
			return
		}
		httputil.InternalErrorResponse(c, err)
		return
	}

	httputil.SuccessResponse(c, DeleteResponse{Deleted: true})
}
