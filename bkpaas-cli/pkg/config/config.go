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

// Package config provides bkpaas-cli config definition
package config

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"

	"github.com/TencentBlueKing/blueking-paas/client/pkg/utils/envx"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/utils/pathx"
)

// 以下变量值可通过环境变量指定
var (
	// FilePath 配置文件所在路径
	FilePath = envx.Get("BKPAAS_CLI_CONFIG", filepath.Join(pathx.GetHomeDir(), ".blueking-paas", "config.yaml"))
)

// G is a global configuration instance that can be used in code logic
var G *Conf

// LoadConf load config from file
func LoadConf(filePath string) (*Conf, error) {
	yamlFile, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}
	conf := &Conf{}
	if err = yaml.Unmarshal(yamlFile, conf); err != nil {
		return nil, err
	}

	// 配置项检查，去除尾斜杠
	conf.PaaSUrl = strings.TrimSuffix(conf.PaaSUrl, "/")
	conf.PaaSApigwUrl = strings.TrimSuffix(conf.PaaSApigwUrl, "/")

	// init global config
	G = conf
	return conf, nil
}

// DumpConf dump global config to file
func DumpConf(filePath string) error {
	contents, err := yaml.Marshal(G)
	if err != nil {
		return err
	}
	if err = os.WriteFile(filePath, contents, 0o644); err != nil {
		return err
	}
	return nil
}

// EnableDebugMode 启用 Debug 模式
func EnableDebugMode() {
	if G != nil {
		G.Debug = true
	}
}

// Conf is bkpaas-cli's config
type Conf struct {
	// PaaSApigwUrl PaaS 平台注册的蓝鲸网关访问地址
	PaaSApigwUrl string `yaml:"paasApigwUrl"`
	// PaaSUrl PaaS 平台访问地址
	PaaSUrl string `yaml:"paasUrl"`
	// CheckTokenUrl 检查 access token API 地址
	CheckTokenUrl string `yaml:"checkTokenUrl"`
	// Username 用户名
	Username string `yaml:"username"`
	// AccessToken apigw 访问凭证
	AccessToken string `yaml:"accessToken"`
	// Debug 调试模式
	Debug bool `yaml:"-"`
}

func (c *Conf) String() string {
	return fmt.Sprintf(
		"configFilePath: %s\n\npaasApigwUrl: %s\npaasUrl: %s\ncheckTokenUrl: %s\nusername: %s\naccessToken: [REDACTED]",
		FilePath,
		G.PaaSApigwUrl,
		G.PaaSUrl,
		G.CheckTokenUrl,
		G.Username,
	)
}
