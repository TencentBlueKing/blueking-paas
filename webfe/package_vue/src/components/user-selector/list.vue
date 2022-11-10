<template>
    <div class="paasng-infinite-list" @scroll="rootScroll">
        <div class="ghost-wrapper" :style="ghostStyle"></div>
        <div class="render-wrapper" ref="content">
            <div class="organization-content">
                <div
                    v-for="(item, index) in renderOrganizationList"
                    :key="item.id"
                    :class="['organization-item', { focus: index === organizationIndex || item.selected }, { 'is-disabled': item.disabled }]"
                    :title="item.full_name"
                    @click.stop="nodeClick(item)">
                    <img class="folder-icon" src="./images/file-close.svg" alt="">
                    <span
                        class="organization-name"
                        :class="item.disabled ? 'is-disabled' : ''">
                        {{ item.name }}
                    </span>
                    <div class="organization-checkbox" v-if="item.showRadio">
                        <span class="node-checkbox"
                            :class="{
                                'is-disabled': item.disabled,
                                'is-checked': item.is_selected,
                                'is-indeterminate': item.indeterminate
                            }"
                            @click.stop="handleNodeClick(item)">
                        </span>
                    </div>
                </div>
            </div>
            <div class="user-content">
                <div
                    v-for="(item, index) in renderUserList"
                    :key="item.id"
                    :class="['user-item', { focus: index === userIndex || item.selected }, { 'is-disabled': item.disabled }]"
                    @click.stop="nodeClick(item)">
                    <img :src="userDefaultAvatar" class="user-icon" alt="">
                    <span
                        class="user-name"
                        :class="item.disabled ? 'is-disabled' : ''"
                        :title="item.username !== '' ? `${item.display_name}(${item.username})` : item.display_name">
                        {{ item.display_name }}
                        <template v-if="item.username !== ''">
                            ({{ item.username }})
                        </template>
                    </span>
                    <div class="user-checkbox" v-if="item.showRadio">
                        <span class="node-checkbox"
                            :class="{
                                'is-disabled': item.disabled,
                                'is-checked': item.is_selected,
                                'is-indeterminate': item.indeterminate
                            }"
                            @click.stop="handleNodeClick(item)">
                        </span>
                    </div>
                </div>
            </div>
        </div>
    </div>

</template>
<script>
    import userDefaultAvatar from './images/personal-user.svg'

    export default {
        name: '',
        props: {
            // 所有数据
            allData: {
                type: Array,
                default: () => []
            },
            // 每个节点的高度
            itemHeight: {
                type: Number,
                default: 32
            },

            focusIndex: {
                type: Number,
                default: -1
            }
        },
        data () {
            return {
                startIndex: 0,
                endIndex: 0,
                userDefaultAvatar: userDefaultAvatar,

                currentFocusIndex: this.focusIndex,

                organizationIndex: -1,
                
                userIndex: -1
            }
        },
        computed: {
            ghostStyle () {
                return {
                    height: this.allData.length * this.itemHeight + 'px'
                }
            },
            // 页面渲染的数据
            renderData () {
                // 渲染在可视区的数据
                return this.allData.slice(this.startIndex, this.endIndex)
            },
            renderOrganizationList () {
                return this.renderData.filter(item => item.type === 'department')
            },
            renderUserList () {
                return this.renderData.filter(item => item.type === 'user')
            }
        },
        watch: {
            focusIndex (value) {
                this.currentFocusIndex = value
                if (value === -1) {
                    this.organizationIndex = -1
                    this.userIndex = -1
                } else {
                    this.computedIndex()
                }
            }
        },
        mounted () {
            this.endIndex = Math.ceil(this.$el.clientHeight / this.itemHeight)
        },
        methods: {
            rootScroll () {
                this.organizationIndex = -1
                this.userIndex = -1
                this.$emit('update:focusIndex', -1)
                this.updateRenderData(this.$el.scrollTop)
            },

            /**
             * 更新可视区渲染的数据列表
             *
             * @param {Number} scrollTop 滚动条高度
             */
            updateRenderData (scrollTop = 0) {
                // 可视区显示的条数
                const count = Math.ceil(this.$el.clientHeight / this.itemHeight)
                // 滚动后可视区新的 startIndex
                const newStartIndex = Math.floor(scrollTop / this.itemHeight)
                // 滚动后可视区新的 endIndex
                const newEndIndex = newStartIndex + count
                this.startIndex = newStartIndex
                this.endIndex = newEndIndex
                this.$refs.content.style.transform = `translate3d(0, ${newStartIndex * this.itemHeight}px, 0)`
            },

            /**
             * 搜索时支持键盘上下键的 hover index 计算
             */
            computedIndex () {
                if (this.renderOrganizationList.length && this.renderUserList.length) {
                    if (this.currentFocusIndex < this.renderOrganizationList.length) {
                        this.organizationIndex = this.currentFocusIndex
                        this.userIndex = -1
                    } else {
                        this.userIndex = this.currentFocusIndex - this.renderOrganizationList.length
                        this.organizationIndex = -1
                    }
                } else if (this.renderOrganizationList.length && !this.renderUserList.length) {
                    this.organizationIndex = this.currentFocusIndex
                } else if (!this.renderOrganizationList.length && this.renderUserList.length) {
                    this.userIndex = this.currentFocusIndex
                } else {
                    this.organizationIndex = -1
                    this.userIndex = -1
                }
            },

            setCheckStatusByIndex () {
                if (this.organizationIndex !== -1) {
                    const currentOrganizationItem = this.renderOrganizationList.find((item, index) => index === this.organizationIndex)
                    if (!currentOrganizationItem.disabled) {
                        currentOrganizationItem.is_selected = !currentOrganizationItem.is_selected
                        this.$emit('on-checked', currentOrganizationItem.is_selected, !currentOrganizationItem.is_selected, currentOrganizationItem.is_selected, currentOrganizationItem)
                    }
                }

                if (this.userIndex !== -1) {
                    const currentUserItem = this.renderUserList.find((item, index) => index === this.userIndex)
                    if (!currentUserItem.disabled) {
                        currentUserItem.is_selected = !currentUserItem.is_selected
                        this.$emit('on-checked', currentUserItem.is_selected, !currentUserItem.is_selected, currentUserItem.is_selected, currentUserItem)
                    }
                }
            },

            /**
             * 点击节点
             *
             * @param {Object} node 当前节点
             */
            nodeClick (node) {
                this.$emit('on-click', node)
                if (!node.disabled) {
                    node.is_selected = !node.is_selected
                    this.$emit('on-checked', node.is_selected, !node.is_selected, node.is_selected, node)
                }
            },

            handleNodeClick (node) {
                node.is_selected = !node.is_selected
                this.$emit('on-checked', node.is_selected, !node.is_selected, true, node)
            }
        }
    }
</script>
<style lang="scss">
    .paasng-infinite-list {
        height: 862px;
        font-size: 14px;
        overflow: auto;
        position: relative;
        overflow: scroll;
        will-change: transform;
        &::-webkit-scrollbar {
            width: 4px;
            background-color: lighten(transparent, 80%);
        }
        &::-webkit-scrollbar-thumb {
            height: 5px;
            border-radius: 2px;
            background-color: #e6e9ea;
        }

        .ghost-wrapper {
            position: absolute;
            left: 0;
            top: 0;
            right: 0;
            z-index: -1;
        }

        .render-wrapper {
            left: 0;
            right: 0;
            top: 0;
            position: absolute;
        }

        .organization-content {
            .organization-item {
                padding: 5px 0;
                border-radius: 2px;
                cursor: pointer;
                &:hover {
                    color: #3a84ff;
                    background: #eef4ff;
                }
                &.is-disabled {
                    color: #c4c6cc;
                    cursor: not-allowed;
                }
                &.is-disabled:hover {
                    background: #eee;
                }
                &.focus {
                    color: #3a84ff;
                    background: #eef4ff;
                }
                .organization-name {
                    display: inline-block;
                    max-width: calc(100% - 72px);
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                    vertical-align: top;
                    &:hover {
                        color: #3a84ff;
                    }
                    &.is-disabled:hover {
                        color: #c4c6cc;
                    }
                }
                .organization-checkbox {
                    margin-right: 5px;
                    float: right;
                }
            }
            .folder-icon {
                position: relative;
                top: 1px;
                width: 18px;
            }
        }

        .user-content {
            .user-item {
                padding: 5px 0;
                border-radius: 2px;
                cursor: pointer;
                &:hover {
                    color: #3a84ff;
                    background: #eef4ff;
                }
                &.is-disabled {
                    color: #c4c6cc;
                    cursor: not-allowed;
                }
                &.is-disabled:hover {
                    background: #eee;
                }
                &.focus {
                    color: #3a84ff;
                    background: #eef4ff;
                }
                .user-name {
                    display: inline-block;
                    max-width: calc(100% - 74px);
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                    vertical-align: top;
                    &:hover {
                        color: #3a84ff;
                    }
                    &.is-disabled:hover {
                        color: #c4c6cc;
                    }
                }
                .user-checkbox {
                    margin-right: 5px;
                    float: right;
                }
            }
            .user-icon {
                position: relative;
                top: 2px;
                width: 18px;
            }
        }

        .node-checkbox {
            display: inline-block;
            position: relative;
            top: 3px;
            width: 16px;
            height: 16px;
            margin: 0 6px 0 0;
            border: 1px solid #979ba5;
            border-radius: 50%;
            &.is-checked {
                border-color: #3a84ff;
                background-color: #3a84ff;
                background-clip: border-box;
                &:after {
                    content: "";
                    position: absolute;
                    top: 2px;
                    left: 5px;
                    width: 4px;
                    height: 8px;
                    border: 2px solid #fff;
                    border-left: 0;
                    border-top: 0;
                    transform-origin: center;
                    transform: rotate(45deg) scaleY(1);
                }
                &.is-disabled {
                    background-color: #dcdee5;
                }
            }
            &.is-disabled {
                border-color: #dcdee5;
                cursor: not-allowed;
            }
            &.is-indeterminate {
                border-width: 7px 4px;
                border-color: #3a84ff;
                background-color: #fff;
                background-clip: content-box;
                &:after {
                    visibility: hidden;
                }
            }
        }
    }
</style>
