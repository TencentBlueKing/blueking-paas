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

let callbackSeed = 0
function JSONP (api, params = {}, options = {}) {
	return new Promise((resolve, reject) => {
		let timer
		const callbackName = `USER_LIST_CALLBACK${callbackSeed++}`
		window[callbackName] = response => {
			timer && clearTimeout(timer)
			document.body.removeChild(script)
			delete window[callbackName]
			resolve(response)
		}
		const script = document.createElement('script')
		script.onerror = event => {
			document.body.removeChild(script)
			delete window[callbackName]
			reject('Get data failed.')
		}
		const query = []
		for(const key in params) {
			query.push(`${key}=${params[key]}`)
		}
		script.src = `${api}?${query.join('&')}&callback=${callbackName}`
		if (options.timeout) {
			setTimeout(() => {
				document.body.removeChild(script)
				delete window[callbackName]
				reject('Get data timeout.')
			}, options.timeout)
		}
		document.body.appendChild(script)
	})
}

const request = {
	async getData (api, params, options) {
		let data = []
		try {
			const response = await JSONP(api, params, options)
			if (response.code !== 0) {
				throw new Error(response)
			}
			data = response.data
		} catch (error) {
			console.error(error.message)
			data = []
		}
		return data
	}
}

export default request
