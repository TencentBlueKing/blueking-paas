package fs

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
	"github.com/gin-gonic/gin"
)

// DownloadFile godoc
//
//	@Summary		Download a file
//	@Description	Download a file from the specified path
//	@Tags			files
//	@Accept			json
//	@Produce		octet-stream
//	@Param			path	query	string	true	"Path to the file to download"
//	@Success		200
//	@Router			/files/download [get]
//
//	@id				DownloadFile
func DownloadFile(c *gin.Context) {
	requestedPath := c.Query("path")
	if requestedPath == "" {
		httputil.BadRequestResponse(c, errors.New("path is required"))
		return
	}

	absPath, err := filepath.Abs(requestedPath)
	if err != nil {
		httputil.BadRequestResponse(c, fmt.Errorf("invalid path: %w", err))
		return
	}

	fileInfo, err := os.Stat(absPath)
	if err != nil {
		if os.IsNotExist(err) {
			httputil.NotFoundResponse(c, err)
			return
		}
		if os.IsPermission(err) {
			httputil.ForbiddenResponse(c, err)
			return
		}
		httputil.BadRequestResponse(c, err)
		return
	}

	if fileInfo.IsDir() {
		httputil.BadRequestResponse(c, errors.New("path must be a file"))
		return
	}

	c.Header("Content-Description", "File Transfer")
	c.Header("Content-Type", "application/octet-stream")
	c.Header("Content-Disposition", fmt.Sprintf(`attachment; filename="%s"`, filepath.Base(absPath)))
	c.Header("Content-Transfer-Encoding", "binary")
	c.Header("Expires", "0")
	c.Header("Cache-Control", "must-revalidate")
	c.Header("Pragma", "public")

	c.File(absPath)
}
