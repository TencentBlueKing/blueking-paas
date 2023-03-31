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

package envs

import (
	"github.com/TencentBlueKing/blueking-paas/client/pkg/utils/envx"
	"github.com/TencentBlueKing/blueking-paas/client/pkg/utils/path"
)

// 以下变量值可通过环境变量指定
var (
	// ConfigFilePath 配置文件所在路径
	ConfigFilePath = envx.Get("BKPAAS_CLI_CONFIG", path.GetHomeDir()+"/.blueking-paas/config.yaml")
)
