package volumefs

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
)

// ErrPathEscape 解析后的路径逃逸出 jail 根, 属越权访问。
var ErrPathEscape = errors.New("path escapes the jail root")

// Resolve returns a lexical path inside the volume jail. Symlinks are checked separately
// before an operation dereferences the resolved path.
func Resolve(rootDir, basePath, relPath string) (full, jailRoot string, err error) {
	if err = validateBasePath(basePath); err != nil {
		return "", "", err
	}
	jailRoot = filepath.Join(rootDir, basePath)
	full = filepath.Join(jailRoot, relPath)
	if !withinJail(full, jailRoot) {
		return "", jailRoot, ErrPathEscape
	}
	return full, jailRoot, nil
}

// ResolveSymlink resolves an existing path and verifies that its target remains in the jail.
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

// ResolveDeletionTarget resolves every parent directory but leaves the final path
// component untouched, so deleting a symlink removes the link rather than its target.
func ResolveDeletionTarget(full, jailRoot string) (string, error) {
	parent, err := ResolveSymlink(filepath.Dir(full), jailRoot)
	if err != nil {
		return "", err
	}
	return filepath.Join(parent, filepath.Base(full)), nil
}

// validateBasePath prevents the jail root itself from escaping the storage root.
func validateBasePath(basePath string) error {
	clean := filepath.Clean(basePath)
	if filepath.IsAbs(basePath) || clean == "." || clean == ".." || strings.HasPrefix(clean, ".."+string(os.PathSeparator)) {
		return ErrPathEscape
	}
	return nil
}

// withinJail reports whether target is jailRoot or one of its descendants.
func withinJail(target, jailRoot string) bool {
	rel, err := filepath.Rel(jailRoot, target)
	return err == nil && rel != ".." && !strings.HasPrefix(rel, ".."+string(os.PathSeparator)) && !filepath.IsAbs(rel)
}
