package volumefs

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
//	@Router			/files [delete]
//
//	@id				PVDeleteFile
func DeleteFile(c *gin.Context) {
	basePath := c.Query("base_path")
	relPath := c.Query("rel_path")
	if basePath == "" || relPath == "" {
		httputil.BadRequestResponse(c, errors.New("base_path and rel_path are required"))
		return
	}

	full, jailRoot, ok := resolveJailed(c, config.G.RootDir, basePath, relPath)
	if !ok {
		return
	}

	target, err := ResolveDeletionTarget(full, jailRoot)
	if err != nil {
		respondErr(c, err)
		return
	}

	info, err := os.Lstat(target)
	if err != nil {
		if os.IsNotExist(err) {
			httputil.SuccessResponse(c, DeleteResponse{Deleted: true})
		} else {
			respondErr(c, err)
		}
		return
	}

	if info.IsDir() {
		httputil.BadRequestResponse(c, errors.New("cannot delete a directory"))
		return
	}

	if err := os.Remove(target); err != nil {
		if os.IsNotExist(err) {
			httputil.SuccessResponse(c, DeleteResponse{Deleted: true})
			return
		}
		respondErr(c, err)
		return
	}
	httputil.SuccessResponse(c, DeleteResponse{Deleted: true})
}
