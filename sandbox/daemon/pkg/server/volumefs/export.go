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

// objectStorageClient 对象存储专用 HTTP client, 带超时避免上游挂起拖垮 daemon。
var objectStorageClient = &http.Client{Timeout: 5 * time.Minute}

// exportMaxSize 允许导出的单文件最大字节数, 超出返回 413。
const exportMaxSize int64 = 104857600 // 100MB

// ExportFile godoc
//
//	@Summary		Export a file to object storage
//	@Description	Read a file from the volume, compute its sha256, and upload it using a presigned URL
//	@Tags			pv
//	@Accept			json
//	@Produce		json
//	@Param			request	body		ExportFileRequest	true	"Export file request"
//	@Success		200		{object}	ExportFileResponse
//	@Router			/files/export [post]
//
//	@id				ExportFile
func ExportFile(c *gin.Context) {
	var req ExportFileRequest
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
	if info.Size() > exportMaxSize {
		httputil.PayloadTooLargeResponse(c, fmt.Errorf("file size %d exceeds limit %d", info.Size(), exportMaxSize))
		return
	}

	f, err := root.Open(name)
	if err != nil {
		respondErr(c, err)
		return
	}
	defer f.Close() // nolint

	sum, err := uploadToObjectStorage(c.Request.Context(), f, info.Size(), req.UploadURL)
	if err != nil {
		httputil.BadGatewayResponse(c, fmt.Errorf("failed to export file: %w", err))
		return
	}

	httputil.SuccessResponse(c, ExportFileResponse{
		Sha256: sum,
		Size:   info.Size(),
		Mtime:  formatTime(info.ModTime()),
	})
}

// uploadToObjectStorage 读文件, 经 TeeReader 边读边算 sha256 并 PUT 到预签名上传 URL, 返回内容 sha256 十六进制串。
func uploadToObjectStorage(ctx context.Context, f *os.File, size int64, uploadURL string) (string, error) {
	hasher := sha256.New()
	// TeeReader: 上传流经 body 的同时把字节喂给 hasher, 单次读取即完成算摘要 + 上传。
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPut, uploadURL, io.TeeReader(f, hasher))
	if err != nil {
		return "", err
	}
	httpReq.ContentLength = size
	httpReq.Header.Set("Content-Type", "application/octet-stream")

	resp, err := objectStorageClient.Do(httpReq)
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
