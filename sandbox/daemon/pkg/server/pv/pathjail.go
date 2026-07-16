package pv

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
)

// ErrPathEscape 表示解析后的路径逃逸出了 jail 根, 属于越权访问
var ErrPathEscape = errors.New("path escapes the jail root")

// JailRoot 计算某个 volume 的 jail 根目录 = rootDir/basePath。
// basePath 由 apiserver 计算下发(形如 app/{volume_uuid_hex}), daemon 视为不可逾越的边界。
func JailRoot(rootDir, basePath string) string {
	return filepath.Join(rootDir, basePath)
}

// Resolve 将用户可控的 relPath 解析为 jail 内的绝对路径(第一道防线)。
//
// filepath.Join 会先做 Clean, 消解 ../ 与多余分隔符; 随后校验结果仍位于 jailRoot 前缀内,
// 从而挡住 ../ 穿越与绝对路径注入。它不解析 symlink —— 那由 ResolveSymlink 兜底。
func Resolve(rootDir, basePath, relPath string) (full, jailRoot string, err error) {
	jailRoot = JailRoot(rootDir, basePath)
	full = filepath.Join(jailRoot, relPath)

	if !withinJail(full, jailRoot) {
		return "", jailRoot, ErrPathEscape
	}
	return full, jailRoot, nil
}

// ResolveSymlink 在真正读写前解析 full 的真实路径, 并做二次前缀校验(第二道防线)。
//
// 它用于挡住用户在存储上创建的、指向 jail 外的 symlink。filepath.EvalSymlinks 要求路径存在,
// 因此仅在确认目标存在后调用; list/stat 对不存在的路径不走此校验。
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

// withinJail 判断 target 是否等于 jailRoot 或位于其下。
// 两侧都必须已被 Clean(filepath.Join / EvalSymlinks 均保证这一点)。
func withinJail(target, jailRoot string) bool {
	if target == jailRoot {
		return true
	}
	return strings.HasPrefix(target, jailRoot+string(os.PathSeparator))
}
