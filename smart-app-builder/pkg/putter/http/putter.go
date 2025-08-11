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
	"io"
	"net/http"
	"net/url"
	"os"
	"time"

	"github.com/go-logr/logr"
	"github.com/pkg/errors"
)

const (
	defaultTimeout = 30 * time.Minute
)

// Putter ...
type Putter struct {
	Logger  logr.Logger
	Timeout time.Duration
}

// NewPutter creates a new Putter with default timeout
func NewPutter(log logr.Logger) *Putter {
	return &Putter{
		Logger:  log,
		Timeout: defaultTimeout,
	}
}

// NewPutterWithTimeOut creates a new Putter with custom timeout
func NewPutterWithTimeOut(log logr.Logger, timeout time.Duration) *Putter {
	return &Putter{
		Logger:  log,
		Timeout: timeout,
	}
}

// Put will put src blob to destUrl
func (p *Putter) Put(src string, destUrl *url.URL) error {
	safeUrl := maskURL(destUrl)

	p.Logger.Info("Start uploading build products to bkrepo", "url", safeUrl, "src", src)

	file, err := os.Open(src)
	if err != nil {
		return errors.Wrap(err, "Failed to open the build product file")
	}
	defer file.Close()

	fileInfo, err := file.Stat()
	if err != nil {
		return errors.Wrap(err, "Failed to obtain file information")
	}

	req, err := http.NewRequest(http.MethodPut, destUrl.String(), file)
	if err != nil {
		return errors.Wrap(err, "Failed to create HTTP request")
	}
	req.Header.Set("Content-Type", "application/octet-stream")
	req.ContentLength = fileInfo.Size()

	p.Logger.Info("Uploading file to bkrepo", "url", safeUrl)

	client := http.Client{Timeout: p.Timeout}
	resp, err := client.Do(req)
	if err != nil {
		return errors.Wrap(err, "Failed to upload to bkrepo")
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		body, _ := io.ReadAll(resp.Body)
		return errors.Errorf("Failed to upload to bkrepo: HTTP %d - %s", resp.StatusCode, string(body))
	}

	p.Logger.Info("Successfully uploaded file to bkrepo", "url", safeUrl, "status", resp.Status)

	return nil
}

func maskURL(u *url.URL) string {
	safe := *u
	if safe.User != nil {
		safe.User = url.UserPassword("***", "***")
	}
	return safe.String()
}
