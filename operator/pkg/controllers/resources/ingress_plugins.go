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

package resources

import (
	"bytes"
	"fmt"
	"strconv"
	"text/template"

	"github.com/lithammer/dedent"

	"bk.tencent.com/paas-app-operator/api/v1alpha1"
	"bk.tencent.com/paas-app-operator/pkg/platform/applications"
)

var (
	registeredIngressPlugins []NginxIngressPlugin
	accessControlTemplate    *template.Template
)

// NginxIngressPlugin ...
type NginxIngressPlugin interface {
	// MakeServerSnippet return a snippet which will be placed in "server" block
	MakeServerSnippet(*v1alpha1.BkApp, []Domain) string
	// MakeConfigurationSnippet return a snippet which will be placed in "location" block
	MakeConfigurationSnippet(*v1alpha1.BkApp, []Domain) string
}

// AccessControlPlugin Access control module for ingress
type AccessControlPlugin struct {
	Config *v1alpha1.AccessControlConfig
}

// MakeServerSnippet return server snippet for access_control module
func (p *AccessControlPlugin) MakeServerSnippet(bkapp *v1alpha1.BkApp, domains []Domain) string {
	return ""
}

// MakeConfigurationSnippet return configuration snippet for access_control module
func (p *AccessControlPlugin) MakeConfigurationSnippet(bkapp *v1alpha1.BkApp, domains []Domain) string {
	if p.Config.RedisConfigKey == "" {
		return ""
	}

	if bkapp == nil || bkapp.Annotations == nil {
		return ""
	}

	info, err := applications.GetBkAppInfo(bkapp)
	if err != nil {
		return ""
	}

	// 判断应用是否启用白名单功能
	if v, ok := bkapp.Annotations[v1alpha1.AccessControlAnnoKey]; !ok {
		return ""
	} else if enableACL, _ := strconv.ParseBool(v); !enableACL {
		return ""
	}

	var tpl bytes.Buffer
	if err = accessControlTemplate.ExecuteTemplate(&tpl, "acl", struct {
		applications.BluekingAppInfo
		RedisConfigKey string
	}{
		*info,
		p.Config.RedisConfigKey,
	}); err != nil {
		return ""
	}
	return tpl.String()
}

func init() {
	var err error

	accessControlTemplate, err = template.New("acl").Parse(dedent.Dedent(`
        # Blow content was configured by access-control plugin, do not edit

        set $bkapp_app_code '{{ .Region }}-{{ .EngineAppName }}';
        set $bkapp_bk_app_code '{{ .AppCode }}';
        set $bkapp_region '{{ .Region }}';
        set $bkapp_env_name '{{ .Environment }}';

        set $acc_redis_server_name '{{ .RedisConfigKey }}';

        access_by_lua_file $module_access_path/main.lua;

        # content of access-control plugin ends`))

	if err != nil {
		panic(fmt.Errorf("failed to new access control template: %w", err))
	}
}

// RegistryPlugin 注册插件
func RegistryPlugin(plugin NginxIngressPlugin) {
	registeredIngressPlugins = append(registeredIngressPlugins, plugin)
}
