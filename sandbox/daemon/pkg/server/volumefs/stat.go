package volumefs

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

	root, name, ok := openJailedRoot(c, config.G.RootDir, req.BasePath, req.RelPath)
	if !ok {
		return
	}
	defer root.Close() // nolint

	info, err := root.Stat(name)
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
		m, err := detectMime(root, name)
		if err != nil {
			respondErr(c, err)
			return
		}
		resp.Mime = m.String()
	}
	httputil.SuccessResponse(c, resp)
}
