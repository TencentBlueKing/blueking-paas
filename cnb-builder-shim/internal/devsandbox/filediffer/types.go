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

package filediffer

// 强制忽略的文件路径前缀
var forceIgnoreFilePathPrefixes = []string{"v3logs"}

// FileAction 文件操作类型
type FileAction string

const (
	// FileActionAdded 文件增加
	FileActionAdded FileAction = "added"
	// FileActionModified 文件变更
	FileActionModified FileAction = "modified"
	// FileActionDeleted 文件删除
	FileActionDeleted FileAction = "deleted"
)

// File 文件详情
type File struct {
	Action  FileAction `json:"action"`
	Path    string     `json:"path"`
	Content string     `json:"content"`
}
