<template lang="html">
    <dropdown
        :options="defaultOptions"
        ref="tooltip">
        <div slot="trigger" style="display: inline">
            <slot name="trigger"></slot>
        </div>
        <div slot="content" :class="['tooltip-default',theme]" @mouseover="mouseoverHandler" @mouseout="mouseoutHandler">
            <a class="tooltip-btn okBtn" @click="ok">{{ okText }}</a>
            <a class="tooltip-btn cancelBtn" @click="cancel">{{ cancelText }}</a>
        </div>
    </dropdown>

</template>

<script>
    import dropdown from '@/components/ui/Dropdown';

    /*

  okText: '确定',
  cancelText: '取消',
  theme: 'tooltip-default',
  openOn: 'click'  click/hover  默认click

*/
    export default {
        components: {
            'dropdown': dropdown
        },
        props: {
            theme: {
                type: String
            },
            okText: {
                type: String
            },
            cancelText: {
                type: String
            },
            openOn: {
                type: Object
            }
        },
        data () {
            return {
                defaultOptions: {
                    openDelay: 2000,
                    hoverOpenDelay: 2000,
                    focusDelay: 2000,
                    position: 'top center',
                    remove: 'click',
                    classes: 'up-theme-ps-arrow',
                    openOn: this.openOn || 'click'
                }
            };
        },
        methods: {
            ok () {
                this.$emit('ok');
            },
            cancel () {
                this.$emit('cancel');
                this.$refs.tooltip.close();
            },
            mouseoverHandler () {
                this.$emit('mouseover');
            },
            mouseoutHandler () {
                this.$emit('mouseout');
            }
        }
    };
</script>

<style lang="scss" scoped>
.tooltip-default {
    font-size: 0;
    letter-spacing: -5px;
    background: #333;
    border: 1px solid #030000;
    .tooltip-btn {
        letter-spacing: 0;
        font-size: 12px;
        color: #FFF;
        text-align: center;
        display: inline-block;
        width: 58px;
        height: 30px;
        line-height: 30px;
        cursor: pointer;
        &:hover {
            color: #ff5656;
        }
        &:first-child {
            width: 59px;
            border-right: 1px solid #030000;
        }
    }
}
</style>
