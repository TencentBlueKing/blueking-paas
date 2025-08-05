/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *	http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

// Package pathx provides path utils
package pathx

import (
	"fmt"
	"path/filepath"
	"runtime"

	"github.com/mitchellh/go-homedir"
)

// GetCurPKGPath 获取当前包的目录
func GetCurPKGPath() string {
	// skip == 1 表示获取上一层函数位置
	_, file, _, ok := runtime.Caller(1)
	if !ok {
		panic("get current pkg's pathx failed")
	}
	return filepath.Dir(file)
}

// GetHomeDir 获取当前用户 Home 目录
func GetHomeDir() string {
	dir, err := homedir.Dir()
	if err != nil {
		panic(fmt.Sprintf("get home dir failed: %s", err))
	}
	return dir
}
