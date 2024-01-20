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

package api

import (
	"net/http"
	"strconv"
	"path/filepath"

	"github.com/gin-gonic/gin"

	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/cmd/devserver/api/service"
	"github.com/TencentBlueking/bkpaas/cnb-builder-shim/pkg/utils"
)

func Deploy(c *gin.Context) {
	token := c.PostForm("token")

	if token != utils.EnvOrDefault("TOKEN", "jwram1lpbnuugmcv") {
		c.String(http.StatusUnauthorized, "invalid token")
		return
	}

	file, err := c.FormFile("file")
	if err != nil {
		c.String(http.StatusBadRequest, "get form err: %s", err.Error())
		return
	}

	fileName := filepath.Base(file.Filename)
	fileDist := utils.EnvOrDefault("UPLOAD_DIR", "/cnb/devcontainer/src/") + fileName
	if err = c.SaveUploadedFile(file, fileDist); err != nil {
		c.String(http.StatusBadRequest, "upload file err: %s", err.Error())
		return
	}

	mgr := service.DeployManager{}
	deployID, err := mgr.Deploy(fileDist)
	if err != nil {
		c.String(http.StatusBadRequest, "deploy err: %s", err.Error())
		return
	}
	c.JSON(http.StatusOK, map[string]interface{}{"deployID": deployID})

}

func DeployResult(c *gin.Context) {
	deployID := c.Param("deployID")
	withLog, _ := strconv.ParseBool(c.Query("log"))

	mgr := service.DeployManager{}
	status, deployLog, err := mgr.Result(deployID, withLog)
	if err != nil {
		c.String(http.StatusBadRequest, "get deploy result err: %s", err.Error())
		return
	}

	if withLog {
		c.JSON(http.StatusOK, map[string]interface{}{"status": status, "log": deployLog})
	} else {
		c.JSON(http.StatusOK, map[string]interface{}{"status": status})
	}

}
