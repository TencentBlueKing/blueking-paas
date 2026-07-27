package volumefs

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
)

// ErrPathEscape indicates an attempt to access a path outside the volume jail.
var ErrPathEscape = errors.New("path escapes the jail root")

// openVolumeRoot opens basePath below rootDir as a traversal-resistant root.
// Both components are opened through os.Root: this keeps a base_path symlink from
// escaping the storage root and makes every subsequent operation symlink-safe.
func openVolumeRoot(rootDir, basePath string) (*os.Root, error) {
	if err := validateBasePath(basePath); err != nil {
		return nil, err
	}

	storageRoot, err := os.OpenRoot(rootDir)
	if err != nil {
		return nil, err
	}
	defer storageRoot.Close() // nolint

	return storageRoot.OpenRoot(basePath)
}

// validateRootPath rejects names which are not contained in an os.Root.
// Empty paths are represented by ".", the root directory itself.
func validateRootPath(name string) (string, error) {
	if name == "" {
		return ".", nil
	}
	clean := filepath.Clean(name)
	if filepath.IsAbs(name) || clean == ".." || strings.HasPrefix(clean, ".."+string(os.PathSeparator)) {
		return "", ErrPathEscape
	}
	return clean, nil
}

// validateBasePath prevents the jail root itself from escaping the storage root.
func validateBasePath(basePath string) error {
	clean, err := validateRootPath(basePath)
	if err != nil || clean == "." {
		return ErrPathEscape
	}
	return nil
}
