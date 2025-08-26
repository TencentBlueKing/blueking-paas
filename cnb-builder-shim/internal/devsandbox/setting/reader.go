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

package setting

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strconv"

	"github.com/pkg/errors"
)

const (
	// UserSettingsDir 用户沙箱 IDE 配置文件所在目录
	UserSettingsDir = "/coder/code-server/User"
	// UserSettingsMaxSize 用户配置文件限制（单位：KB）
	UserSettingsMaxSize = 512
	// UserSettingsSizeEnvVarKey 用户配置文件大小限制环境变量名
	UserSettingsSizeEnvVarKey = "SETTINGS_MAX_SIZE"
	// UserSettingsFileName 用户配置文件名
	UserSettingsFileName = "settings.json"
)

var (
	// UserSettingsNotFound 用户配置文件不存在
	UserSettingsNotFound = errors.New("configuration file not found")
	// UserSettingsTooLarge 用户配置文件过大
	UserSettingsTooLarge = errors.New("configuration file is too large")
)

// UserSettingsReader 用户配置读取器
type UserSettingsReader struct {
	Dir string
}

// NewUserSettingsReader ...
func NewUserSettingsReader() *UserSettingsReader {
	return &UserSettingsReader{Dir: UserSettingsDir}
}

// Read 读取用户配置
func (r *UserSettingsReader) Read() (map[string]any, error) {
	filePath := filepath.Join(r.Dir, UserSettingsFileName)

	info, err := os.Stat(filePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, UserSettingsNotFound
		}
		return nil, errors.Wrap(err, "os.Stat settings.json")
	}

	// 检查以限制文件大小
	maxSizeBytes := r.getUserSettingsMaxSize()
	if info.Size() > maxSizeBytes {
		return nil, UserSettingsTooLarge
	}

	// 读取用户配置文件
	content, err := os.ReadFile(filePath)
	if err != nil {
		return nil, errors.Wrap(err, "read settings.json")
	}

	// 解析成 map[string]any
	var userSettings map[string]any
	if err = json.Unmarshal(content, &userSettings); err != nil {
		return nil, errors.Wrap(err, "parse settings.json")
	}

	return userSettings, nil
}

// getUserSettingsMaxSize 获取用户配置文件大小限制
func (r *UserSettingsReader) getUserSettingsMaxSize() int64 {
	if envSize, ok := os.LookupEnv(UserSettingsSizeEnvVarKey); ok {
		if parsedSize, err := strconv.Atoi(envSize); err == nil && parsedSize > 0 {
			return int64(parsedSize) * 1024
		}
	}
	return int64(UserSettingsMaxSize) * 1024
}
