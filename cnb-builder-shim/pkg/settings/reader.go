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

package settings

import (
	"encoding/json"
	"github.com/pkg/errors"
	"os"
	"path/filepath"
	"strconv"
)

var (
	// SettingsDir 用户沙箱 IDE 配置文件所在目录
	SettingsDir          = "/coder/code-server/User"
	UserSettingsNotFound = errors.New("configuration file not found")
	UserSettingsTooLarge = errors.New("configuration file is too large")
)

const (
	// UserSettingsMaxSize 用户配置文件限制（单位：KB）
	UserSettingsMaxSize       = 512
	UserSettingsSizeEnvVarKey = "SETTINGS_MAX_SIZE_KB"
	UserSettingsFileName      = "settings.json"
)

type Reader struct {
	DirPath string
}

var NewReader = func(dirPath string) Reader {
	return Reader{DirPath: dirPath}
}

func (r *Reader) Read() (map[string]any, error) {
	filePath := filepath.Join(r.DirPath, UserSettingsFileName)

	info, err := os.Stat(filePath)
	if os.IsNotExist(err) {
		return nil, UserSettingsNotFound
	}
	if err != nil {
		return nil, err
	}

	maxSizeBytes := r.getUserSettingsMaxSize()
	if info.Size() > maxSizeBytes {
		return nil, UserSettingsTooLarge
	}

	content, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}

	var settingsMap map[string]any
	if err := json.Unmarshal(content, &settingsMap); err != nil {
		return nil, errors.Wrap(err, "failed to parse settings.json")
	}

	return settingsMap, nil
}

func (r *Reader) getUserSettingsMaxSize() int64 {
	maxSizeKB := UserSettingsMaxSize
	if envSize, exists := os.LookupEnv(UserSettingsSizeEnvVarKey); exists {
		if parsedSize, err := strconv.Atoi(envSize); err == nil && parsedSize > 0 {
			maxSizeKB = parsedSize
		}
	}
	return int64(maxSizeKB) * 1024
}
