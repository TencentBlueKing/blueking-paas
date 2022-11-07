import * as __SimpleMDE__ from "simplemde"
import "simplemde/dist/simplemde.min.css"
import Vue from 'vue'

const SimpleMDEComponent = {
    name: 'simple-mde-editor',
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
        disabled: {
            type: Boolean,
            default: false
        }
    },
    data: function () {
        return {
            editor: undefined
        }
    },
    mounted: function () {
        if(this.editor === undefined){
            this.editor = new __SimpleMDE__({
                element: this.$refs.editor,
                initialValue: this.value,
            })

            this.editor.codemirror.on('change', (instance, changeObj) => {
                let value = this.editor.codemirror.getValue();
                if (this.source) {
                    // 回显到前端
                    this.source.innerHTML = value
                    this.source.value = value
                }
                this.$emit("change", value)
            })
        }
    },
    watch: {
        value: function (newValue, oldValue) {
            if (newValue !== this.editor.codemirror.getValue()) {
                this.editor.codemirror.setValue(newValue)
            }
        },
        disabled: function (newValue, oldValue) {
            this.editor.codemirror.options.readOnly = newValue
        }
    },
    render: function (h) {
        return h('textarea', {
            ref: 'editor',
            attrs: {
                class: 'simple-mde-editor'
            }
        })
    },
}

// Vue 组件形式
export default SimpleMDEComponent

// Class 形式
export const SimpleMDE = class {
    constructor (source, markdown=undefined) {
        this.source = source
        if (markdown === undefined){
            markdown = source.innerHTML
        }

        let el = document.createElement("simple-mde-editor")
        source.parentNode.append(el)
        source.style.display = 'none'

        this.instance = new (Vue.extend(SimpleMDEComponent))({
            el,
            propsData: {
                source,
                value: markdown
            }
        })
    }

    get value () {
        return this.instance.editor.value()
    }

    set value (value) {
        this.instance.editor.value(value)
    }
}