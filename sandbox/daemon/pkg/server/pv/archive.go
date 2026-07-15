package pv

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/config"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

// ArchiveFile godoc
//
//	@Summary		Archive a file to bkrepo
//	@Description	Read the file, compute sha256, and PUT it to the presigned upload URL
//	@Tags			pv
//	@Accept			json
//	@Produce		json
//	@Param			request	body		ArchiveRequest	true	"Archive request"
//	@Success		200		{object}	ArchiveResponse
//	@Router			/files/cfs/archive [post]
//
//	@id				ArchiveFile
func ArchiveFile(c *gin.Context) {
	var req ArchiveRequest
	if !bindJSON(c, &req) {
		return
	}

	full, jailRoot, ok := resolveJailed(c, config.G.CFSRoot, req.BasePath, req.RelPath)
	if !ok {
		return
	}

	real, err := ResolveSymlink(full, jailRoot)
	if err != nil {
		if errors.Is(err, ErrPathEscape) {
			httputil.ForbiddenResponse(c, err)
			return
		}
		if os.IsNotExist(err) {
			httputil.NotFoundResponse(c, err)
			return
		}
		httputil.InternalErrorResponse(c, err)
		return
	}

	info, err := os.Stat(real)
	if err != nil {
		httputil.InternalErrorResponse(c, err)
		return
	}
	if info.IsDir() {
		httputil.BadRequestResponse(c, errors.New("path must be a file"))
		return
	}
	if info.Size() > config.G.ArchiveMaxSize {
		httputil.PayloadTooLargeResponse(c, fmt.Errorf("file size %d exceeds limit %d", info.Size(), config.G.ArchiveMaxSize))
		return
	}

	sum, err := uploadFile(c.Request.Context(), real, info.Size(), req.UploadURL)
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

// uploadFile 读取文件, 边读边算 sha256, 并 PUT 到临时上传 URL。返回内容的 sha256 十六进制串。
//
// TODO(Q-upload-verb): 上传动词本期按 PUT 实现, 待与 bkrepo 联调确认是否需改 multipart。
func uploadFile(ctx context.Context, path string, size int64, uploadURL string) (string, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close() // nolint

	hasher := sha256.New()
	// TeeReader: 上传流经 body 的同时把字节喂给 hasher, 单次读取即完成算摘要 + 上传
	body := io.TeeReader(f, hasher)

	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPut, uploadURL, body)
	if err != nil {
		return "", err
	}
	httpReq.ContentLength = size
	httpReq.Header.Set("Content-Type", "application/octet-stream")

	resp, err := http.DefaultClient.Do(httpReq)
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
