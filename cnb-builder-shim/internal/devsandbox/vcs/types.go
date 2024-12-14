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

// Package vcs 版本控制系统（VersionControlSystem）
package vcs

import (
	"path"
	"slices"
	"strings"
)

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

// Files 文件列表
type Files []File

// AsTree 转换成目录树形式
func (files Files) AsTree() *DirTree {
	// 按照文件路径排序
	slices.SortFunc(files, func(a, b File) int {
		return strings.Compare(a.Path, b.Path)
	})

	root := DirTree{Name: ""}
	var cur *DirTree
	for _, f := range files {
		parts := strings.Split(f.Path, "/")
		cur = &root
		// 循环创建目录树
		for _, part := range parts[:len(parts)-1] {
			if part == "" {
				continue
			}
			exists := false
			for _, dir := range cur.Dirs {
				if dir.Name == part {
					cur = dir
					exists = true
					break
				}
			}
			if !exists {
				cur.Dirs = append(cur.Dirs, &DirTree{Name: part})
				cur = cur.Dirs[len(cur.Dirs)-1]
			}
		}
		// 目录树格式下，路径即为文件名
		f.Path = parts[len(parts)-1]
		cur.Files = append(cur.Files, f)
	}

	// 压缩目录树，避免过多的嵌套层级
	return root.Compress()
}

// DirTree 目录树
type DirTree struct {
	Name  string     `json:"name"`
	Dirs  []*DirTree `json:"dirs"`
	Files Files      `json:"files"`
}

// Compress 压缩
func (t *DirTree) Compress() *DirTree {
	// 根目录不需要压缩，只有子目录需要
	for idx, d := range t.Dirs {
		t.Dirs[idx] = d.compress(d.Name)
	}
	return t
}

func (t *DirTree) compress(prefix string) *DirTree {
	if len(t.Files) == 0 && len(t.Dirs) == 1 {
		subDir := t.Dirs[0]
		subDir.Name = path.Join(prefix, subDir.Name)
		return subDir.compress(subDir.Name)
	}

	for idx, d := range t.Dirs {
		t.Dirs[idx] = d.compress(d.Name)
	}
	return t
}
