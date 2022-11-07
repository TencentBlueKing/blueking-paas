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