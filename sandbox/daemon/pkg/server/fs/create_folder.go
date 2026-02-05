package fs

import (
	"errors"
	"io"
	"os"
	"strconv"

	"github.com/gin-gonic/gin"

	"github.com/bkpaas/sandbox/daemon/pkg/server/httputil"
)

// CreateFolder creates a folder.
func CreateFolder(c *gin.Context) {
	var request CreateFolderRequest

	if err := c.ShouldBindJSON(&request); err != nil {
		if errors.Is(err, io.EOF) {
			httputil.BadRequestResponse(c, errors.New("request body is empty or missing"))
		} else {
			httputil.BadRequestResponse(c, err)
		}
		return
	}

	// Get the permission mode from query params, default to 0755
	mode := request.Mode
	var perm os.FileMode = 0o755
	if mode != "" {
		modeNum, err := strconv.ParseUint(mode, 8, 32)
		if err != nil {
			httputil.BadRequestResponse(c, errors.New("invalid mode format"))
			return
		}
		perm = os.FileMode(modeNum)
	}

	if err := os.MkdirAll(request.Path, perm); err != nil {
		httputil.BadRequestResponse(c, err)
		return
	}

	httputil.CreatedSuccessResponse(c)
}
