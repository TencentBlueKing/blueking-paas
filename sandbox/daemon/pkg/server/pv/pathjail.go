package pv

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
)

// ErrPathEscape 解析后的路径逃逸出 jail 根, 属越权访问。
var ErrPathEscape = errors.New("path escapes the jail root")

// JailRoot 返回 volume 的 jail 根 = rootDir/basePath。basePath 由 apiserver 下发, daemon 视为不可逾越的边界。
func JailRoot(rootDir, basePath string) string {
	return filepath.Join(rootDir, basePath)
}

// Resolve 将 relPath 解析为 jail 内绝对路径(第一道防线): Join 消解 ../ 与绝对路径,
// 再校验仍在 jailRoot 前缀内。不解析 symlink, 那由 ResolveSymlink 兜底。
func Resolve(rootDir, basePath, relPath string) (full, jailRoot string, err error) {
	if err = validateBasePath(basePath); err != nil {
		return "", "", err
	}
	jailRoot = JailRoot(rootDir, basePath)
	full = filepath.Join(jailRoot, relPath)
	if !withinJail(full, jailRoot) {
		return "", jailRoot, ErrPathEscape
	}
	return full, jailRoot, nil
}

// ResolveSymlink 在读写前解析真实路径并二次校验前缀(第二道防线), 挡住指向 jail 外的 symlink。要求路径已存在。
func ResolveSymlink(full, jailRoot string) (real string, err error) {
	real, err = filepath.EvalSymlinks(full)
	if err != nil {
		return "", err
	}
	if !withinJail(real, jailRoot) {
		return "", ErrPathEscape
	}
	return real, nil
}

// validateBasePath 拒绝 basePath 中的 .. 穿越, 防 jailRoot 本身逸出 rootDir。
func validateBasePath(basePath string) error {
	clean := filepath.Clean(basePath)
	if clean == ".." || strings.HasPrefix(clean, ".."+string(os.PathSeparator)) {
		return ErrPathEscape
	}
	return nil
}

// withinJail 判断 target 是否等于 jailRoot 或位于其下(两侧须已 Clean)。
func withinJail(target, jailRoot string) bool {
	if target == jailRoot {
		return true
	}
	return strings.HasPrefix(target, jailRoot+string(os.PathSeparator))
}
