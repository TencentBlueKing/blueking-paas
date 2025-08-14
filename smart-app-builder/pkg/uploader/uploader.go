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

package uploader

import (
	"net/url"

	"github.com/go-logr/logr"
)

type Uploader interface {
	Upload(src string, destUrl *url.URL) error
}

func NewUploader(scheme string, logger logr.Logger) Uploader {
	switch scheme {
	case "file":
		return NewFsUploader(logger)
	case "http", "https":
		return NewHttpUploader(logger)
	default:
		return nil
	}
}
