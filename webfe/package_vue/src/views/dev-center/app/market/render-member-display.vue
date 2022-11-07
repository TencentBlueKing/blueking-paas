<template>
    <div class="paasng-member-display-wrapper">
        <label class="label">
            <i :class="['paasng-icon', 'icon', icon]"></i>
            <span class="name">{{ title }}</span>
        </label>
        <div class="content">
            <div v-for="(item, index) in data"
                :key="index"
                class="member-item"
                :title="isDepartment ? item.name : item.display_name !== '' ? `${item.name}(${item.display_name})` : item.name">
                <span class="member-name">
                    {{ item.name }}
                </span>
                <template v-if="!isDepartment && item.display_name">
                    <span class="display_name">({{ item.display_name }})</span>
                </template>
                <i class="paasng-icon paasng-close-circle-shape remove-icon" v-if="isEdit" @click="handleDelete(item.id)"></i>
            </div>
        </div>
    </div>
</template>
<script>
    export default {
        name: '',
        props: {
            data: {
                type: Array,
                default: () => []
            },
            type: {
                type: String,
                default: 'user'
            },
            mode: {
                type: String,
                default: 'edit'
            }
        },
        computed: {
            icon () {
                return this.type === 'user' ? 'paasng-user-shape' : 'paasng-organization';
            },
            title () {
                return this.type === 'user' ? this.$t('用户') : this.$t('组织');
            },
            isDepartment () {
                return this.type === 'department';
            },
            isEdit () {
                return this.mode === 'edit';
            }
        },
        methods: {
            handleDelete (payload) {
                this.$emit('on-delete', payload);
            }
        }
    };
</script>
<style lang="scss" scoped>
    .paasng-member-display-wrapper {
        color: #63656e;
        .label {
            display: inline-block;
            font-size: 12px;
            .icon {
                display: inline-block;
                color: #3a84ff;
                vertical-align: middle;
            }
            .name {
                display: inline-block;
                font-weight: 700;
                vertical-align: middle;
            }
        }
        .content {
            .member-item {
                position: relative;
                display: inline-block;
                margin: 0 6px 6px 0;
                padding: 0 10px;
                line-height: 22px;
                background: #f5f6fa;
                border: 1px solid #dcdee5;
                border-radius: 2px;
                font-size: 12px;
                &:hover {
                    .remove-icon {
                        display: block;
                    }
                }
                .member-name {
                    display: inline-block;
                    max-width: 200px;
                    line-height: 17px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                    vertical-align: text-top;
                    .count {
                        color: #c4c6cc;
                    }
                }
                .count,
                .display_name {
                    display: inline-block;
                    vertical-align: top;
                }
                .remove-icon {
                    display: none;
                    position: absolute;
                    top: -6px;
                    right: -6px;
                    cursor: pointer;
                }
            }
        }
    }
</style>
