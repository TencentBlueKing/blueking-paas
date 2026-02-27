package fs

import (
	"errors"
	"os"

	"github.com/gin-gonic/gin"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

// DeleteFile godoc
//
//	@Summary		Delete a file or folder
//	@Description	Delete a file or folder at the specified path, with optional recursive deletion for directories
//	@Tags			files
//	@Accept			json
//	@Produce		json
//	@Param			path		query	string	true	"Path to the file or folder to delete"
//	@Param			recursive	query	bool	false	"Enable recursive deletion for directories"
//	@Success		204
//	@Router			/files/ [delete]
//
//	@id				DeleteFile
func DeleteFile(c *gin.Context) {
	path := c.Query("path")
	if path == "" {
		httputil.BadRequestResponse(c, errors.New("path is required"))
		return
	}

	// Check if recursive deletion is requested
	recursive := c.Query("recursive") == "true"

	// Get file info to check if it's a directory
	info, err := os.Stat(path)
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

	// If it's a directory and recursive flag is not set, return error
	if info.IsDir() && !recursive {
		httputil.BadRequestResponse(c, errors.New("cannot delete directory without recursive flag"))
		return
	}

	var deleteErr error
	if recursive {
		deleteErr = os.RemoveAll(path)
	} else {
		deleteErr = os.Remove(path)
	}

	if deleteErr != nil {
		httputil.BadRequestResponse(c, deleteErr)
		return
	}

	httputil.NoContentResponse(c)
}
