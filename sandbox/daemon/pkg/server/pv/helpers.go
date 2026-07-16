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

// builtinMimesByExt 是 daemon 自维护的标准 MIME 映射, 在 detectMimeByExt 中优先级最高,
// 使常见扩展名的取值不随宿主漂移。标准库在 unix 上先读 FreeDesktop /usr/share/mime/globs2,
// 再退回 /etc/mime.types, 二者都会给出 application/x-yaml 这类厂商前缀值, 且在精简镜像下可能
// 缺失; 此表固化标准取值, 优先采用 IANA 已注册型(text/markdown, text/csv, application/yaml,
// application/sql), 无正式注册的取社区通用写法并在此固化(text/x-go 等)。
var builtinMimesByExt = map[string]string{
	// 纯文本 / 标记 / 配置
	".txt":        "text/plain",
	".log":        "text/plain",
	".md":         "text/markdown",
	".csv":        "text/csv",
	".tsv":        "text/tab-separated-values",
	".yaml":       "application/yaml",
	".yml":        "application/yaml",
	".toml":       "application/toml",
	".sql":        "application/sql",
	".ini":        "text/plain",
	".cfg":        "text/plain",
	".conf":       "text/plain",
	".env":        "text/plain",
	".properties": "text/plain",
	".lock":       "text/plain",
	".diff":       "text/x-diff",
	".patch":      "text/x-diff",
	".dockerfile": "text/x-dockerfile",
	".mk":         "text/x-makefile",
	// 源代码 (text/* 前缀自动归入可预览文本, 无需在 isTextMime 登记)
	".go":    "text/x-go",
	".py":    "text/x-python",
	".sh":    "text/x-shellscript",
	".c":     "text/x-c",
	".h":     "text/x-c",
	".cpp":   "text/x-c++",
	".cc":    "text/x-c++",
	".cxx":   "text/x-c++",
	".hpp":   "text/x-c++",
	".hxx":   "text/x-c++",
	".java":  "text/x-java-source",
	".kt":    "text/x-kotlin",
	".kts":   "text/x-kotlin",
	".scala": "text/x-scala",
	".rs":    "text/rust",
	".rb":    "text/x-ruby",
	".lua":   "text/x-lua",
	".swift": "text/x-swift",
	".r":     "text/x-r",
	".pl":    "text/x-perl",
	".pm":    "text/x-perl",
	".php":   "text/x-php",
	".proto": "text/x-protobuf",
	// 图片 (标准库 builtinTypesLower 未内置, 精简镜像下会缺失)
	".bmp":  "image/bmp",
	".ico":  "image/vnd.microsoft.icon",
	".tiff": "image/tiff",
	".heic": "image/heic",
	// 压缩包
	".tar": "application/x-tar",
	".gz":  "application/gzip",
	".tgz": "application/gzip",
	".bz2": "application/x-bzip2",
	".xz":  "application/x-xz",
	".7z":  "application/x-7z-compressed",
	".rar": "application/vnd.rar",
	".zip": "application/zip",
	// 音视频
	".mp3":  "audio/mpeg",
	".ogg":  "application/ogg",
	".wav":  "audio/wav",
	".flac": "audio/flac",
	".mp4":  "video/mp4",
	".m4a":  "audio/mp4",
	".webm": "video/webm",
	".avi":  "video/x-msvideo",
	".mov":  "video/quicktime",
	".mkv":  "video/x-matroska",
	// 文档
	".rtf":  "application/rtf",
	".doc":  "application/msword",
	".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
	".xls":  "application/vnd.ms-excel",
	".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
	".ppt":  "application/vnd.ms-powerpoint",
	".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
	// 字体
	".woff":  "font/woff",
	".woff2": "font/woff2",
	".ttf":   "font/ttf",
	".otf":   "font/otf",
	".eot":   "application/vnd.ms-fontobject",
	// 其它二进制
	".apk": "application/vnd.android.package-archive",
	".jar": "application/java-archive",
	".exe": "application/vnd.microsoft.portable-executable",
	".iso": "application/x-iso9660-image",
	".rpm": "application/x-rpm",
	".dmg": "application/x-apple-diskimage",
}

// detectMimeByExt 仅按扩展名推断 MIME, 不读取文件内容。用于列表等批量场景。
// 解析顺序: 内置兜底表 builtinMimesByExt → 标准库 mime.TypeByExtension → application/octet-stream。
// 内置表优先, 使常见文本/配置/代码扩展名的判定不随宿主 /etc/mime.types 变化
// (alpine 等精简镜像默认无该文件), 其余扩展名交由标准库兜底(如 .png/.pdf/.svg)。
func detectMimeByExt(name string) string {
	ext := strings.ToLower(filepath.Ext(name))
	if m, ok := builtinMimesByExt[ext]; ok {
		return m
	}
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
		"application/yaml", "application/x-yaml", "application/toml", "application/sql":
		return true
	}
	return false
}

// formatTime 将时间统一格式化为 RFC3339 UTC(如 2026-06-24T10:23:11Z)。
func formatTime(t time.Time) string {
	return t.UTC().Format(time.RFC3339)
}
