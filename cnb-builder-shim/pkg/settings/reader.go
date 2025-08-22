package settings

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
)

const (
	// DefaultMaxSizeKB 默认最大文件大小限制（KB）
	DefaultMaxSizeKB = 512
	SizeEnvVar       = "SETTINGS_MAX_SIZE_KB"
	SettingsFileName = "settings.json"
)

type Reader struct {
	DirPath string
}

func NewReader(dirPath string) *Reader {
	return &Reader{DirPath: dirPath}
}

func (r *Reader) Read() ([]byte, error) {
	// 获取最大文件大小
	maxSizeKB := DefaultMaxSizeKB
	if envSize, exists := os.LookupEnv(SizeEnvVar); exists {
		if parsedSize, err := strconv.Atoi(envSize); err == nil && parsedSize > 0 {
			maxSizeKB = parsedSize
		}
	}
	maxSizeBytes := int64(maxSizeKB) * 1024

	filePath := filepath.Join(r.DirPath, SettingsFileName)

	info, err := os.Stat(filePath)
	if os.IsNotExist(err) {
		return nil, fmt.Errorf("configuration file not found")
	}

	fileSizeKB := float64(info.Size()) / 1024
	if info.Size() > maxSizeBytes {
		return nil, fmt.Errorf("configuration file too large (%.1fKB > %dKB)", fileSizeKB, maxSizeKB)
	}

	content, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read file: %w", err)
	}

	return content, nil
}
