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
//	@Param			request	query		StatRequest	true	"Stat request"
//	@Success		200		{object}	StatResponse
//	@Router			/files/stat [get]
//
//	@id				StatFile
func StatFile(c *gin.Context) {
	var req StatRequest
	if !bindQuery(c, &req) {
		return
	}
	c.Header("Cache-Control", "no-store")

	full, _, ok := resolveJailed(c, config.G.RootDir, req.BasePath, req.RelPath)
	if !ok {
		return
	}

	// Lstat 不跟随 symlink: stat 语义是"查在不在", 不存在非错误。
	info, err := os.Lstat(full)
	if err != nil {
		if os.IsNotExist(err) {
			httputil.SuccessResponse(c, StatResponse{Exists: false, Path: req.RelPath})
		} else {
			respondErr(c, err)
		}
		return
	}

	resp := StatResponse{
		Exists:     true,
		Path:       req.RelPath,
		Size:       info.Size(),
		ModifiedAt: formatTime(info.ModTime()),
	}
	if !info.IsDir() {
		// 不读内容(避免 symlink 嗅探逃逸), 与 list 一致按扩展名判定。
		resp.Mime = detectMimeByExt(info.Name())
	}
	httputil.SuccessResponse(c, resp)
}
