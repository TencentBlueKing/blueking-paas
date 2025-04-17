package utils

import (
	"io"
	"os"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

var CopyDir = utils.CopyDir

// CopyFile copy file
func CopyFile(src, dst string) error {
	source, err := os.Open(src)
	if err != nil {
		return err
	}
	defer source.Close()

	destination, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer destination.Close()

	_, err = io.Copy(destination, source)
	return err
}
