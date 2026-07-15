package pv

import (
	"errors"
	"io"
	"net/http"
	"os"
	"unicode/utf8"

	"github.com/gin-gonic/gin"
	"golang.org/x/text/encoding/simplifiedchinese"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/config"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

// PreviewFile godoc
//
//	@Summary		Preview a text file
//	@Description	Return the first max_bytes of a text file as UTF-8; 415 for non-text types
//	@Tags			pv
//	@Accept			json
//	@Produce		plain
//	@Param			request	body	PreviewRequest	true	"Preview request"
//	@Success		200
//	@Header			200	{string}	X-Truncated	"whether the content was truncated"
//	@Router			/files/cfs/preview [post]
//
//	@id				PreviewFile
func PreviewFile(c *gin.Context) {
	var req PreviewRequest
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

	// 仅文本类可预览; 非文本类返回 415, 前端改用 download_url + disposition=inline。
	// 按内容嗅探(魔数)判定, 兼顾被改名伪装的文件。
	mimeType := detectMime(real)
	if !isTextMime(mimeType) {
		httputil.UnsupportedMediaTypeResponse(c, errors.New("file is not previewable"))
		return
	}

	maxBytes := req.MaxBytes
	if maxBytes <= 0 {
		maxBytes = config.G.PreviewMaxBytes
	}

	f, err := os.Open(real)
	if err != nil {
		httputil.InternalErrorResponse(c, err)
		return
	}
	defer f.Close() // nolint

	// 多读 1 字节以判定是否发生截断
	raw, err := io.ReadAll(io.LimitReader(f, maxBytes+1))
	if err != nil {
		httputil.InternalErrorResponse(c, err)
		return
	}

	// 文件级截断: 读到的字节数超过上限, 说明文件还有更多内容。
	fileTruncated := int64(len(raw)) > maxBytes
	if fileTruncated {
		raw = raw[:maxBytes]
	}

	// 规整为合法 UTF-8。toUTF8 会在字符边界裁掉被字节截断拆散的多字节字符,
	// 避免按字节切分 UTF-8 / GBK 字符后产生乱码。
	content := toUTF8(raw)

	// GBK -> UTF-8 会使字节数膨胀(中文 2 -> 3), 解码后可能超过 maxBytes,
	// 需在字符边界再次裁剪, 保证输出不超过上限且不拆散字符。
	capped := int64(len(content)) > maxBytes
	if capped {
		content = capUTF8(content, maxBytes)
	}

	if fileTruncated || capped {
		c.Header("X-Truncated", "true")
	} else {
		c.Header("X-Truncated", "false")
	}
	c.Data(http.StatusOK, "text/plain; charset=utf-8", content)
}

// toUTF8 将内容规整为合法 UTF-8, 永不返回包含不完整多字节字符的字节流:
//  1. 已是合法 UTF-8 -> 原样返回;
//  2. 仅因尾部存在不完整的多字节字符而非法(常见于按字节截断的 UTF-8 文件)
//     -> 裁掉尾部不完整字符后返回合法前缀, 避免误判为 GBK 而产生乱码;
//  3. 否则尝试按 GBK 解码(简体中文常见), 解码结果再裁一次尾部不完整字符;
//  4. 仍失败则原样返回(前端按 UTF-8 尽力渲染)。
func toUTF8(raw []byte) []byte {
	if utf8.Valid(raw) {
		return raw
	}
	if trimmed := trimTrailingIncompleteRune(raw); trimmed != nil {
		return trimmed
	}
	if decoded, err := simplifiedchinese.GBK.NewDecoder().Bytes(raw); err == nil && utf8.Valid(decoded) {
		return decoded
	} else if utf8.Valid(decoded) {
		// 解码过程中遇到尾部不完整的 GBK 字符会返回 err, 但已解码前缀仍是合法 UTF-8。
		if trimmed := trimTrailingIncompleteRune(decoded); trimmed != nil {
			return trimmed
		}
	}
	return raw
}

// trimTrailingIncompleteRune 处理「按字节截断拆散了末尾多字节字符」的情形:
// 若 raw 主体是合法 UTF-8、仅末尾残留一个不完整的字符, 则返回裁掉该残留后的合法前缀;
// 否则(例如整体是 GBK, 全程都不是合法 UTF-8)返回 nil, 交由上层走 GBK 解码分支。
func trimTrailingIncompleteRune(raw []byte) []byte {
	// 自末尾回退, 跳过所有续字节(0x80~0xBF), 定位最后一个字符的起始字节。
	start := len(raw)
	for n := 0; n < utf8.UTFMax && start > 0; n++ {
		start--
		if utf8.RuneStart(raw[start]) {
			break
		}
	}
	if start >= len(raw) || start < 0 {
		return nil
	}
	prefix := raw[:start]
	tail := raw[start:]
	// 前缀必须本身合法, 尾部必须是一个「期望更多续字节但未收齐」的残缺字符,
	// 二者同时成立才认定是截断拆散, 否则视作非 UTF-8 内容(交 GBK 分支)。
	if !utf8.Valid(prefix) || utf8.FullRune(tail) || !validRunePrefix(tail) {
		return nil
	}
	return prefix
}

// validRunePrefix 判断 b 是否为一个多字节字符的合法(但不完整)前缀:
// 首字节是合法的多字节起始字节, 其余为合法续字节, 且长度小于该字符应有长度。
func validRunePrefix(b []byte) bool {
	if len(b) == 0 {
		return false
	}
	first := b[0]
	var expect int
	switch {
	case first < 0x80:
		return false // ASCII: 不存在「不完整前缀」
	case first < 0xC0:
		return false // 续字节不应作为字符起始
	case first < 0xE0:
		expect = 2
	case first < 0xF0:
		expect = 3
	case first < 0xF8:
		expect = 4
	default:
		return false
	}
	if len(b) >= expect {
		return false // 字节已收齐, 不属于「不完整前缀」
	}
	for _, c := range b[1:] {
		if c < 0x80 || c >= 0xC0 {
			return false // 续字节应在 0x80~0xBF
		}
	}
	return true
}

// capUTF8 将 b 裁剪到不超过 max 字节, 且不拆散末尾的多字节字符。
func capUTF8(b []byte, max int64) []byte {
	if int64(len(b)) <= max {
		return b
	}
	end := int(max)
	for end > 0 && !utf8.RuneStart(b[end]) {
		end--
	}
	return b[:end]
}
