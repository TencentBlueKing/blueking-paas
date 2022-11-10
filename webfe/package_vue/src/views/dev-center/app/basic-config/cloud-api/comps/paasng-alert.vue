<template>
    <div :class="['paasng-alert', theme]">
        <i class="bk-icon icon-info"></i>
        <div class="alert-content">
            <div class="alert-title">
                <slot name="title">
                    {{ title }}
                </slot>
            </div>
        </div>
    </div>
</template>
<script>
    export default {
        name: '',
        props: {
            title: {
                type: String,
                default: ''
            },
            theme: {
                type: String,
                default: 'primary'
            }
        }
    };
</script>
<style lang="scss" scoped>
    .paasng-alert {
        position: relative;
        display: flex;
        padding: 8px 10px;
        font-size: 12px;
        color: #63656e;
        border: 1px solid;
        border-radius: 2px;
        &.primary {
            border-color: #c5daff;
            background-color: #f0f8ff;
            i {
                color: #3a84ff;
            }
        }
        i {
            margin-right: 8px;
            font-size: 16px;
        }
        .alert-content {
            display: flex;
            flex-direction: column;
            margin-right: auto;
            .alert-title {
                line-height: 16px;
            }
        }
    }
</style>
