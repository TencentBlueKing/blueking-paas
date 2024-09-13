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
package http

import (
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"

	"github.com/go-logr/logr"
	"github.com/mholt/archiver/v3"
	"github.com/pkg/errors"
)

var unexpectedBlobTypeError = errors.New("unexpected blob file type, must be one of .rar, .zip, .tar.gz, .tar")

// Fetcher ...
type Fetcher struct {
	Logger logr.Logger
}

// NewFetcher ...
func NewFetcher(log logr.Logger) *Fetcher {
	return &Fetcher{log}
}

// Fetch will download blob from url, and unzip to destDir
func (f *Fetcher) Fetch(srcUrl string, destDir string) error {
	url, err := url.Parse(srcUrl)
	if err != nil {
		return err
	}

	f.Logger.Info(fmt.Sprintf("Downloading %s%s...", url.Host, url.Path))
	file, err := downloadBlob(url.String())
	if err != nil {
		return err
	}
	defer os.RemoveAll(file.Name())

	mediaType, err := classifyFile(file)
	if err != nil {
		return err
	}

	var arc archiver.Unarchiver

	switch mediaType {
	case "application/zip":
		arc = archiver.NewZip()
	case "application/x-gzip":
		arc = archiver.NewTarGz()
	case "application/x-rar-compressed":
		arc = archiver.NewZip()
	case "application/octet-stream":
		arc, err = archiver.ByHeader(file)
		if err != nil {
			return unexpectedBlobTypeError
		}
	default:
		return unexpectedBlobTypeError
	}

	err = arc.Unarchive(file.Name(), destDir)
	if err != nil {
		return errors.Wrapf(err, "Failed to decompress file from %s%s", url.Host, url.Path)
	}

	f.Logger.Info(fmt.Sprintf("Download %s%s to path %q successfully", url.Host, url.Path, destDir))
	return nil
}

func downloadBlob(blobURL string) (*os.File, error) {
	resp, err := http.Get(blobURL)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, errors.Errorf("failed to get blob %s", blobURL)
	}

	file, err := os.CreateTemp("", "")
	if err != nil {
		return nil, err
	}

	_, err = io.Copy(file, resp.Body)
	if err != nil {
		return nil, err
	}

	_, err = file.Seek(0, 0)
	if err != nil {
		return nil, err
	}

	return file, nil
}

func classifyFile(reader io.ReadSeeker) (string, error) {
	buf := make([]byte, 512)
	_, err := reader.Read(buf)
	if err != nil {
		return "", err
	}

	_, err = reader.Seek(0, 0)
	if err != nil {
		return "", err
	}

	return http.DetectContentType(buf), nil
}
