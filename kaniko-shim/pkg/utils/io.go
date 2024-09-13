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
package utils

import (
	"io"
)

// WriterWatcher provide io.Writer interface
type WriterWatcher struct {
	Signal chan int
	Writer io.Writer
}

// Write writes the p to wrapped Writer, and send a signal to chan Signal
// If write succeed, will send the number of bytes written to chan Signal, otherwise, send -1 to mean err
func (w *WriterWatcher) Write(p []byte) (n int, err error) {
	n, err = w.Writer.Write(p)
	if err != nil {
		w.Signal <- -1
	} else {
		w.Signal <- n
	}
	return
}

// NewWriterWrapper return a WriterWatcher instance wrapped the given writer w
func NewWriterWrapper(w io.Writer, signal chan int) *WriterWatcher {
	return &WriterWatcher{Signal: signal, Writer: w}
}
