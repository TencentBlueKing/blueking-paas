<template>
  <div class="release-timeline-warp">
    <bk-timeline
      ext-cls="timeline-cls"
      :list="lineList"
      @select="dataSelect"
    />
  </div>
</template>
<script>
    export default {
        props: {
            list: {
                type: Array,
                default () {
                    return [];
                }
            }
        },
        data () {
            return {
                lineList: []
            };
        },
        watch: {
            list (val) {
                if (val.length) {
                    this.lineList = val;
                }
            }
        },
        mounted () {

        },
        methods: {
            dataSelect () {}
        }
    };
</script>
<style lang="scss">
    .timeline-cls .bk-timeline-item-primary .bk-timeline-icon{
        color: #fff;
        border: none;
    }
    .timeline-cls .bk-timeline-item-primary .bk-timeline-icon .bk-timeline-icon-inner .deploy-round-loading{
        position: absolute;
        top: -2px;
    }
    .release-timeline-warp {
        .timeline-cls {
            .bk-timeline-dot {
                border-left: none;
                padding-bottom: 16px;
                margin-top: 0;
                .bk-timeline-title {
                    color: #C4C6CC;
                }
                &::before {
                    transform: translateX(-1px);
                }
                &::after {
                    content: '';
                    display: inline-block;
                    position: absolute;
                    top: 3px;
                    left: -2px;
                    height: 22px;
                    border-left: 1px dashed #d8d8d8;
                }
                &:last-child {
                    &::after {
                        border-left: none;
                    }
                    &::before {
                        transform: translateX(-1px);
                    }
                }
            }
            .bk-timeline-item-success{
                border-left: none;
                .bk-timeline-title {
                    color: #63656E;
                }
                &::after {
                    border-left: 1px dashed #30d878;
                }
            }
            .bk-timeline-item-danger {
                .bk-timeline-title {
                    color: #63656E;
                }
            }
        }
    }
</style>
