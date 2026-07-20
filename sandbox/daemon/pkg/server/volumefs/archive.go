package volumefs

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"github.com/gin-gonic/gin"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/config"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

// archiveClient 上传专用 HTTP client, 带超时避免上游挂起拖垮 daemon。
var archiveClient = &http.Client{Timeout: 5 * time.Minute}

// archiveMaxSize 允许归档的单文件最大字节数, 超出返回 413。
const archiveMaxSize int64 = 104857600 // 100MB

// ArchiveFile godoc
//
//	@Summary		Archive a file to bkrepo
//	@Description	Read the file, compute sha256, and PUT it to the presigned upload URL
//	@Tags			pv
//	@Accept			json
//	@Produce		json
//	@Param			request	body		ArchiveRequest	true	"Archive request"
//	@Success		200		{object}	ArchiveResponse
//	@Router			/files/archive [post]
//
//	@id				ArchiveFile
func ArchiveFile(c *gin.Context) {
	var req ArchiveRequest
	if !bindJSON(c, &req) {
		return
	}

	root, name, ok := openJailedRoot(c, config.G.RootDir, req.BasePath, req.RelPath)
	if !ok {
		return
	}
	defer root.Close() // nolint

	info, err := root.Stat(name)
	if err != nil {
		respondErr(c, err)
		return
	}
	if info.IsDir() {
		httputil.BadRequestResponse(c, errors.New("path must be a file"))
		return
	}
	if info.Size() > archiveMaxSize {
		httputil.PayloadTooLargeResponse(c, fmt.Errorf("file size %d exceeds limit %d", info.Size(), archiveMaxSize))
		return
	}

	f, err := root.Open(name)
	if err != nil {
		respondErr(c, err)
		return
	}
	defer f.Close() // nolint

	sum, err := uploadFile(c.Request.Context(), f, info.Size(), req.UploadURL)
	if err != nil {
		httputil.BadGatewayResponse(c, fmt.Errorf("archive failed: %w", err))
		return
	}

	httputil.SuccessResponse(c, ArchiveResponse{
		Sha256: sum,
		Size:   info.Size(),
		Mtime:  formatTime(info.ModTime()),
	})
}

// uploadFile 读文件, 经 TeeReader 边读边算 sha256 并 PUT 到临时上传 URL, 返回内容 sha256 十六进制串。
func uploadFile(ctx context.Context, f *os.File, size int64, uploadURL string) (string, error) {
	hasher := sha256.New()
	// TeeReader: 上传流经 body 的同时把字节喂给 hasher, 单次读取即完成算摘要 + 上传。
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPut, uploadURL, io.TeeReader(f, hasher))
	if err != nil {
		return "", err
	}
	httpReq.ContentLength = size
	httpReq.Header.Set("Content-Type", "application/octet-stream")

	resp, err := archiveClient.Do(httpReq)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close() // nolint

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		msg, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
		return "", fmt.Errorf("upload responded %d: %s", resp.StatusCode, string(msg))
	}
	return hex.EncodeToString(hasher.Sum(nil)), nil
}
