package volumefs

import (
	"errors"
	"io"
	"net/http"
	"strconv"
	"unicode/utf8"

	"github.com/gin-gonic/gin"
	"golang.org/x/text/encoding/simplifiedchinese"

	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/config"
	"github.com/TencentBlueking/blueking-paas/sandbox/daemon/pkg/server/httputil"
)

// previewMaxBytes 文本预览默认截断上限(字节), max_bytes 超过或 <=0 时钳到此值。
const previewMaxBytes int64 = 65536

// PreviewFile godoc
//
//	@Summary		Preview a text file
//	@Description	Return the first max_bytes of a text file as UTF-8; 415 for non-text types
//	@Tags			pv
//	@Accept			json
//	@Produce		plain
//	@Param			request	query	PreviewRequest	true	"Preview request"
//	@Success		200
//	@Header			200	{string}	X-Truncated	"whether the content was truncated"
//	@Router			/files/preview [get]
//
//	@id				PreviewFile
func PreviewFile(c *gin.Context) {
	var req PreviewRequest
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
		respondErr(c, err)
		return
	}
	if info.IsDir() {
		httputil.BadRequestResponse(c, errors.New("path must be a file"))
		return
	}

	// 按内容嗅探(魔数)判定, 兼顾被改名伪装的文件; 非文本返回 415 交前端 inline 下载。
	m, err := detectMime(root, name)
	if err != nil {
		respondErr(c, err)
		return
	}

	if !isTextMime(m.String()) {
		httputil.UnsupportedMediaTypeResponse(c, errors.New("file is not previewable"))
		return
	}

	// max_bytes 客户端可控, 钳到上限防内存放大; <=0 用默认上限。
	maxBytes := req.MaxBytes
	if maxBytes <= 0 || maxBytes > previewMaxBytes {
		maxBytes = previewMaxBytes
	}

	f, err := root.Open(name)
	if err != nil {
		respondErr(c, err)
		return
	}
	defer f.Close() // nolint

	// 多读 1 字节判定是否截断。
	raw, err := io.ReadAll(io.LimitReader(f, maxBytes+1))
	if err != nil {
		httputil.InternalErrorResponse(c, err)
		return
	}

	truncated := int64(len(raw)) > maxBytes
	if truncated {
		raw = raw[:maxBytes]
	}

	// 规整为合法 UTF-8: toUTF8 在字符边界裁掉被截断拆散的多字节字符; GBK->UTF-8 膨胀后超限则再裁一次。
	content := toUTF8(raw)
	if int64(len(content)) > maxBytes {
		content = capUTF8(content, maxBytes)
		truncated = true
	}

	c.Header("X-Truncated", strconv.FormatBool(truncated))
	c.Data(http.StatusOK, "text/plain; charset=utf-8", content)
}

// toUTF8 将内容规整为合法 UTF-8, 永不返回含不完整多字节字符的字节流:
//  1. 已合法 -> 原样返回;
//  2. 仅尾部不完整(常见于按字节截断) -> 裁掉尾部返回前缀, 避免误判为 GBK 产生乱码;
//  3. 否则尝试按 GBK 解码(简体中文常见), 解码结果再裁一次尾部;
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
		// 解码遇尾部不完整 GBK 字符会返回 err, 但已解码前缀仍是合法 UTF-8。
		if trimmed := trimTrailingIncompleteRune(decoded); trimmed != nil {
			return trimmed
		}
	}
	return raw
}

// trimTrailingIncompleteRune 处理末尾被字节截断拆散的多字节字符: 若主体合法、仅尾部残留
// 一个不完整字符, 返回裁掉后的前缀; 否则(如整体是 GBK)返回 nil, 交上层走 GBK 解码分支。
func trimTrailingIncompleteRune(raw []byte) []byte {
	// 自末尾回退, 跳过续字节(0x80~0xBF), 定位最后一个字符的起始字节。
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
	// 前缀必须合法, 尾部须是"期望更多续字节但未收齐"的残缺字符, 二者同时成立才认定是截断拆散。
	if !utf8.Valid(prefix) || utf8.FullRune(tail) || !validRunePrefix(tail) {
		return nil
	}
	return prefix
}

// validRunePrefix 判断 b 是否为某多字节字符的合法但不完整前缀。
func validRunePrefix(b []byte) bool {
	if len(b) == 0 {
		return false
	}
	first := b[0]
	var expect int
	switch {
	case first < 0x80, first < 0xC0:
		return false // ASCII 或续字节, 不存在"不完整前缀"
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
		return false
	}
	for _, c := range b[1:] {
		if c < 0x80 || c >= 0xC0 {
			return false // 续字节应在 0x80~0xBF
		}
	}
	return true
}

// capUTF8 将 b 裁到不超过 max 字节, 且不拆散末尾多字节字符。
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
