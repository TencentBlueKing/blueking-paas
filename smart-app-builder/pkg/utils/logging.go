package utils

import (
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/logging"
	"github.com/go-logr/logr"
)

var logger = logging.Default()

// GetLogger returns the default logger
func GetLogger() logr.Logger {
	return logger
}
