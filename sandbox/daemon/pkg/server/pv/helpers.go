package pv

import (
	"mime"
	"path/filepath"
	"strings"
	"time"

	"github.com/gabriel-vasile/mimetype"
)

// detectMime 按文件内容嗅探 MIME 类型(魔数), 失败时回退到扩展名。
// 用于单个文件的精确判定(stat / preview): 仅读取文件头部, 即便大文件代价也低。
// 不适合列表等批量场景——逐个开文件开销大, 列表请用 detectMimeByExt。
func detectMime(path string) string {
	if m, err := mimetype.DetectFile(path); err == nil && m != nil {
		return stripCharset(m.String())
	}
	return detectMimeByExt(filepath.Base(path))
}

// detectMimeByExt 仅按扩展名推断 MIME, 不读取文件内容。用于列表等批量场景。
// 解析顺序: 内置兜底表 builtinMimesByExt → 标准库 mime.TypeByExtension → application/octet-stream。
// 内置表优先, 使常见文本/配置/代码扩展名的判定不随宿主 /etc/mime.types 变化
// (alpine 等精简镜像默认无该文件), 其余扩展名交由标准库兜底(如 .png/.pdf/.svg)。
func detectMimeByExt(name string) string {
	ext := strings.ToLower(filepath.Ext(name))
	if m := mime.TypeByExtension(ext); m != "" {
		return stripCharset(m)
	}
	return "application/octet-stream"
}

// stripCharset 去掉 MIME 串中的 charset 等参数, 如 "text/html; charset=utf-8" → "text/html"。
func stripCharset(m string) string {
	if idx := strings.IndexByte(m, ';'); idx != -1 {
		return strings.TrimSpace(m[:idx])
	}
	return m
}

// isTextMime 判断 MIME 是否属于可文本预览的类型。
func isTextMime(m string) bool {
	if strings.HasPrefix(m, "text/") {
		return true
	}
	switch m {
	case "application/json", "application/xml", "application/javascript",
		"application/x-yaml", "application/yaml":
		return true
	}
	return false
}

// formatTime 将时间统一格式化为 RFC3339 UTC(如 2026-06-24T10:23:11Z)。
func formatTime(t time.Time) string {
	return t.UTC().Format(time.RFC3339)
}
