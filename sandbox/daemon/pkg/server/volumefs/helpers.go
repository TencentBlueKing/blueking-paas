package volumefs

import (
	"strings"
	"time"
)

// isTextMime 判断是否为可文本预览的类型。
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

// formatTime 统一格式化为 RFC3339 UTC。
func formatTime(t time.Time) string {
	return t.UTC().Format(time.RFC3339)
}
