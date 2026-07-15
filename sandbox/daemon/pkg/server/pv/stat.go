package pv

import (
	"os"

	"github.com/gin-gonic/gin"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/config"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

// StatFile godoc
//
//	@Summary		Stat a file in a volume
//	@Description	Return metadata of base_path/rel_path; returns 200 with exists=false if not found
//	@Tags			pv
//	@Accept			json
//	@Produce		json
//	@Param			request	body		StatRequest	true	"Stat request"
//	@Success		200		{object}	StatResponse
//	@Router			/files/cfs/stat [post]
//
//	@id				StatFile
func StatFile(c *gin.Context) {
	var req StatRequest
	if !bindJSON(c, &req) {
		return
	}

	full, _, ok := resolveJailed(c, config.G.CFSRoot, req.BasePath, req.RelPath)
	if !ok {
		return
	}

	// 用 Lstat: stat 语义是"查在不在", 不跟随 symlink, 不存在非错误
	info, err := os.Lstat(full)
	if err != nil {
		if os.IsNotExist(err) {
			httputil.SuccessResponse(c, StatResponse{Exists: false, Path: req.RelPath})
			return
		}
		if os.IsPermission(err) {
			httputil.ForbiddenResponse(c, err)
			return
		}
		httputil.InternalErrorResponse(c, err)
		return
	}

	resp := StatResponse{
		Exists:     true,
		Path:       req.RelPath,
		Size:       info.Size(),
		ModifiedAt: formatTime(info.ModTime()),
	}
	if !info.IsDir() {
		resp.Mime = detectMime(full)
	}
	httputil.SuccessResponse(c, resp)
}
