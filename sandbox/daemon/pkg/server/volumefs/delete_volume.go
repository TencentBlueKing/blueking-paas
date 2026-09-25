package volumefs

import (
	"errors"
	"fmt"
	"os"

	"github.com/gin-gonic/gin"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/config"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

// DeleteVolume godoc
//
//	@Summary		Delete an entire volume directory
//	@Description	Remove base_path (a Volume's shared-storage sub-directory) and everything under it; deleting a missing directory is idempotent
//	@Tags			pv
//	@Accept			json
//	@Produce		json
//	@Param			base_path	query		string	true	"volume storage path issued by apiserver, must match app/{32 hex chars}"
//	@Success		200			{object}	DeleteResponse
//	@Router			/files/volume [delete]
//
//	@id				PVDeleteVolume
func DeleteVolume(c *gin.Context) {
	basePath := c.Query("base_path")
	if basePath == "" {
		httputil.BadRequestResponse(c, errors.New("base_path is required"))
		return
	}
	if err := validateVolumeBasePath(basePath); err != nil {
		httputil.BadRequestResponse(c, err)
		return
	}

	// base_path 自身就是要删除的目标, 必须在存储根上直接操作
	storageRoot, err := os.OpenRoot(config.G.RootDir)
	if err != nil {
		httputil.InternalErrorResponse(c, err)
		return
	}
	defer storageRoot.Close() // nolint

	info, err := storageRoot.Lstat(basePath)
	switch {
	case errors.Is(err, os.ErrNotExist):
		// 幂等: Volume 从未被挂载过时, 共享存储上本来就没有该目录
		httputil.SuccessResponse(c, DeleteResponse{Deleted: true})
		return
	case err != nil:
		respondErr(c, err)
		return
	case !info.IsDir():
		// 目标位置被普通文件或符号链接占据属于异常数据, 拒绝删除, 交人工处理
		httputil.BadRequestResponse(c, fmt.Errorf("not a directory: %q", basePath))
		return
	}

	// 失败 (如权限/IO 错误) 时目录可能只被删掉一部分, 目录本身仍保留, 由调用方重试补完
	if err := storageRoot.RemoveAll(basePath); err != nil {
		respondErr(c, err)
		return
	}
	httputil.SuccessResponse(c, DeleteResponse{Deleted: true})
}
