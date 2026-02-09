package fs

import (
	"errors"

	"github.com/gin-gonic/gin"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

// UploadFile godoc
//
//	@Summary		Upload a file
//	@Description	Upload a file to the specified destination path
//	@Tags			files
//	@Accept			multipart/form-data
//	@Produce		json
//	@Param			file		formData	file	true	"File to upload"
//	@Param			destPath	formData	string	true	"Destination path for the uploaded file"
//	@Success		204
//	@Router			/files/upload [post]
//
//	@id				UploadFile
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
