package utils

import (
	"context"
	"io/fs"
	"os"
	"path/filepath"

	"github.com/mholt/archives"
	"github.com/samber/lo"
)

// ArchiveTGZ 将 sourceDir 打包成 destTGZ
func ArchiveTGZ(sourceDir, destTGZ string) error {
	entries, err := os.ReadDir(sourceDir)
	if err != nil {
		return err
	}

	ctx := context.TODO()
	files, err := archives.FilesFromDisk(ctx, nil, lo.SliceToMap(entries, func(entry fs.DirEntry) (string, string) {
		return filepath.Join(sourceDir, entry.Name()), ""
	}))
	if err != nil {
		return err
	}

	if err = os.MkdirAll(filepath.Dir(destTGZ), 0o744); err != nil {
		return err
	}

	out, err := os.Create(destTGZ)
	if err != nil {
		return err
	}
	defer out.Close()

	format := archives.CompressedArchive{
		Compression: archives.Gz{},
		Archival:    archives.Tar{},
	}

	err = format.Archive(context.TODO(), out, files)
	if err != nil {
		return err
	}
	return nil
}
