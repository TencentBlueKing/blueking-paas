package fs

import (
	"errors"

	"github.com/gin-gonic/gin"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

// UploadFile handles file uploads.
func UploadFile(c *gin.Context) {
	dst := c.PostForm("destPath")
	if dst == "" {
		httputil.BadRequestResponse(c, errors.New("destPath is required"))
		return
	}

	file, err := c.FormFile("file")
	if err != nil {
		httputil.BadRequestResponse(c, err)
		return
	}

	if err = c.SaveUploadedFile(file, dst); err != nil {
		httputil.BadRequestResponse(c, err)
		return
	}

	httputil.NoContentResponse(c)
}
