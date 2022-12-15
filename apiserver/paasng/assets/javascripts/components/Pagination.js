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
const querystring = require('querystring');
import { bkPagination } from 'BkMagicVue'

const Pagination = {
    extends: bkPagination,
    methods: {
        goto: function (page = 1) {
            let limit = this.realityLimit
            let offset = limit * (page - 1)
            let query = {limit, offset}
            
            let prefix = window.location.href
            if (prefix.indexOf("?") > 0) {
                query = {...querystring.parse(prefix.substr(prefix.indexOf("?") + 1)), ...query}
                prefix = prefix.substr(0, prefix.indexOf("?"))
            }
            query = querystring.stringify(query)
            window.location.href = `${prefix}?${query}`
        }
    },
    created: function (){
        this.$on("change", (page) => {
            this.$bkLoading({title: '加载中'})
            this.$emit("update:current", page)
            this.goto(page)
        })

        this.$on("limit-change", (limit) => {
            this.$bkLoading({title: '加载中'})
            this.$emit("update:current", 1)
            this.realityLimit = limit
            this.goto(1)
        })
    },
}

export default Pagination