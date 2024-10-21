/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

package utils

import (
	"io/fs"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"

	"github.com/mholt/archiver/v3"
	"github.com/pkg/errors"
)

// CreateSymlink create symlink if the symlink not exist
func CreateSymlink(oldname, newname string) error {
	if _, err := os.Stat(newname); os.IsNotExist(err) {
		return os.Symlink(oldname, newname)
	}
	return nil
}

// CopyDir copies a directory from the source path to the destination path.
//
// The function takes two string parameters:
// - srcDir: the source directory path.
// - destDir: the destination directory path.
//
// The function returns an error if any error occurs during the copy process.
func CopyDir(srcDir, destDir string) error {
	return filepath.Walk(srcDir, func(path string, info fs.FileInfo, err error) error {
		if err != nil {
			return err
		}

		relPath, _ := filepath.Rel(srcDir, path)
		destPath := filepath.Join(destDir, relPath)

		if info.IsDir() {
			if iErr := os.MkdirAll(destPath, info.Mode()); iErr != nil {
				return iErr
			}
		} else {
			// 读取源文件内容
			content, iErr := os.ReadFile(path)
			if iErr != nil {
				return iErr
			}
			// 写入目标文件
			if iErr = os.WriteFile(destPath, content, info.Mode()); iErr != nil {
				return iErr
			}
		}

		return nil
	})
}

// Unzip extracts the contents of a zip file to a specified directory.
//
// srcFilePath is the path to the zip file.
// distDir is the directory where the extracted files will be placed.
// Returns an error if there was a problem extracting the zip file.
func Unzip(srcFilePath, distDir string) error {
	z := archiver.NewZip()
	if err := z.Unarchive(srcFilePath, distDir); err != nil {
		return errors.Wrap(err, "unzip error")
	}
	return nil
}

// ExtractTarGz extracts the contents of a tar.gz file to a specified directory.
//
// srcFilePath is the path to the zip file.
// distDir is the directory where the extracted files will be placed.
// Returns an error if there was a problem extracting the tar gz file.
func ExtractTarGz(srcFilePath, distDir string) error {
	z := archiver.NewTarGz()
	if err := z.Unarchive(srcFilePath, distDir); err != nil {
		return errors.Wrap(err, "extract tar.gz error")
	}
	return nil
}

// Chownr changes the ownership of a file or directory and all its contents recursively.
//
// The function takes three parameters:
// - filePath: a string representing the path to the file or directory.
// - uid: an integer representing the user ID to set as the owner.
// - gid: an integer representing the group ID to set as the owner.
//
// The function returns an error if the ownership change fails, or nil if it succeeds.
func Chownr(filePath string, uid, gid int) error {
	return filepath.Walk(filePath, func(path string, info fs.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if err = os.Chown(path, uid, gid); err != nil {
			// ignore error if no such file or directory.
			// e.g. some source file of symlink may not exist
			if !strings.Contains(err.Error(), "no such file or directory") {
				return err
			}
		}

		return nil
	})
}

// SortedCompareFile reads the contents of two files, removes empty lines, sorts the lines
// in each file alphabetically, and compares the sorted lines
// for equality.
func SortedCompareFile(filePath1, filePath2 string) (bool, error) {
	lines1, err := readAndSortLines(filePath1)
	if err != nil {
		return false, err
	}

	lines2, err := readAndSortLines(filePath2)
	if err != nil {
		return false, err
	}

	return reflect.DeepEqual(lines1, lines2), nil
}

func readAndSortLines(filePath string) ([]string, error) {
	content, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}

	lines := []string{}
	rawLines := strings.Split(string(content), "\n")

	for _, line := range rawLines {
		trimmedLine := strings.TrimSpace(line)
		if trimmedLine != "" {
			lines = append(lines, trimmedLine)
		}
	}

	sort.Strings(lines)

	return lines, nil
}
