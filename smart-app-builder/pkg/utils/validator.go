package utils

import (
	"github.com/blang/semver/v4"
	"github.com/pkg/errors"
)

// ValidateVersion check whether version string match semantic version
func ValidateVersion(version string) error {
	if version == "" {
		return errors.New("version is empty")
	}
	v, err := semver.Make(version)
	if err != nil {
		return errors.Wrapf(err, "version '%s' not match semantic version", version)
	}
	if err = v.Validate(); err != nil {
		return errors.Wrapf(err, "version '%s' not match semantic version", version)
	}

	return nil
}
