package volumefs

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
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

// volumeBasePathPattern matches the shared-storage sub-directory of one Volume:
// "app/" plus the 32 lowercase hex chars of its UUID (Volume.storage_path on the
// apiserver side).
var volumeBasePathPattern = regexp.MustCompile(`^app/[0-9a-f]{32}$`)

// validateVolumeBasePath rejects any base_path that is not a Volume's storage path.
// Volume deletion removes base_path itself, so an unconstrained value could wipe the
// storage root or an unrelated directory.
func validateVolumeBasePath(basePath string) error {
	if !volumeBasePathPattern.MatchString(basePath) {
		return fmt.Errorf("base_path %q must match app/{32 hex chars}", basePath)
	}
	return nil
}
