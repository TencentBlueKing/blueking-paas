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
import * as jsoneditor from 'jsoneditor'
import "jsoneditor/dist/jsoneditor.css"
import Vue from 'vue'


const JsonEditorComponent = {
    name: 'json-editor',
    model: {
        prop: 'value',
        event: 'change'
    },
    props: {
        value: {
            default: function () {
                return {}
            }
        },
        source: {
            type: Node,
            default: undefined,
        },
        schema: {
            type: Object,
            default: undefined,
        },
        nullable: {
            type: Boolean,
            default: function () {
                return false
            }
        }
    },
    data: function () {
        return {
            editor: undefined
        }
    },
    mounted: function () {
        if(this.editor === undefined){
            this.editor = new jsoneditor(this.$refs.editor, {
                mode: 'code',
                schema: this.schema,
                onChange: () => {
                    let jsonStr = this.editor.getText()
                    // 回显到前端
                    if (this.source) {
                        this.source.innerHTML = jsonStr
                        this.source.value = jsonStr
                    }

                    try {
                        this.$emit("change", this.editor.get())
                    } catch (e) {
                        if (this.nullable && this.editor.getText() == '') {
                            this.$emit("change", null)
                        }
                        throw e
                    }
                }
            }, this.value)
        }
    },
    watch: {
        value: function (newValue, oldValue) {
            if (JSON.stringify(newValue) !== JSON.stringify(this.editor.get())) {
                this.editor.set(newValue)
            }
        },
        schema: function (newSchema) {
            if (this.editor !== undefined) {
                this.editor.setSchema(newSchema)
            }
        }
    },
    render: function (h) {
        return h('div', {
            ref: 'editor',
            attrs: {
                class: 'ace-jsoneditor'
            }
        })
    },
}

// Vue 组件形式
export default JsonEditorComponent

// Class 形式
export const JsonEditor = class {
    constructor (source, json=undefined, nullable=false) {
        this.source = source
        this.nullable = nullable
        if (json == undefined){
            try {
                json = JSON.parse(source.innerHTML)
            } catch (error) {
                console.error(error)
                json = {}
            }
        }

        let el = document.createElement("json-editor")
        source.parentNode.append(el)
        source.style.display = 'none'

        this.instance = new (Vue.extend(JsonEditorComponent))({
            el,
            propsData: {
                source,
                value: json
            }
        })
    }

    get json () {
        try {
            return this.instance.editor.get()
        } catch (e) {
            if (this.nullable && this.instance.editor.getText() == '') {
                return null
            }
            throw e
        }
    }

    set json (value) {
        if (typeof value === "string") {
            this.instance.editor.setText(value)
        } else {
            this.instance.editor.set(value)
        }
    }
}