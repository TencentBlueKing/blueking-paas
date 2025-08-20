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

package putter

import (
	"encoding/base64"
	"io"
	"net/http"
	"net/url"
	"os"
	"time"

	"github.com/go-logr/logr"
	"github.com/pkg/errors"
)

const (
	defaultTimeout = 10 * time.Minute
)

// HttpPutter ...
type HttpPutter struct {
	Logger  logr.Logger
	timeout time.Duration
}

// NewHttpPutter creates a new Putter with default timeout
func NewHttpPutter(log logr.Logger) *HttpPutter {
	h := &HttpPutter{Logger: log}
	h.SetTimeout(defaultTimeout)
	return h
}

// SetTimeout sets the timeout for the putter and returns itself
func (h *HttpPutter) SetTimeout(timeout time.Duration) *HttpPutter {
	h.timeout = timeout
	return h
}

// Put will put src blob to destUrl
func (h *HttpPutter) Put(src string, destUrl *url.URL) error {
	safeUrl := maskURL(destUrl)

	h.Logger.Info("Start uploading file", "src", src, "url", safeUrl)

	file, err := os.Open(src)
	if err != nil {
		return errors.Wrap(err, "Failed to open the file")
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
	if destUrl.User != nil {
		username := destUrl.User.Username()
		password, hasPassword := destUrl.User.Password()
		if hasPassword {
			auth := "Basic " + base64.StdEncoding.EncodeToString([]byte(username+":"+password))
			req.Header.Set("Authorization", auth)
		}
	}

	h.Logger.Info("Uploading file", "src", src, "url", safeUrl)

	client := http.Client{Timeout: h.timeout}
	resp, err := client.Do(req)
	if err != nil {
		return errors.Wrap(err, "Failed to upload file")
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		body, errRead := io.ReadAll(resp.Body)
		if errRead != nil {
			h.Logger.Error(errRead, "Failed to read response body")
			return errors.Errorf("Failed to upload file: HTTP %d - unable to read response body", resp.StatusCode)
		}
		return errors.Errorf("Failed to upload file: HTTP %d - %s", resp.StatusCode, string(body))
	}

	h.Logger.Info("Successfully uploaded file", "url", safeUrl, "status", resp.Status)

	return nil
}

// maskURL hides the username and password in the URL for logging purposes,
func maskURL(u *url.URL) string {
	if u == nil {
		return ""
	}

	ru := *u
	if _, has := ru.User.Password(); has {
		ru.User = url.UserPassword("xxxxx", "xxxxx")
	}

	return ru.String()
}
