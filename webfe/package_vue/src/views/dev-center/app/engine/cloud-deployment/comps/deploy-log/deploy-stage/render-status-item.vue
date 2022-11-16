<template>
  <div
    class="paas-deploy-process-status-item"
    :class="getClass()"
  >
    <span>
      {{ status === 'Running' ? $t('成功') : ['Starting', 'Pending'].includes(status) ? $t('部署中') : $t('异常') }}
      <template v-if="abnormalCount > 0">({{ abnormalCount }})</template>
    </span>
  </div>
</template>
<script>
    export default {
        name: '',
        props: {
            status: {
                type: String,
                default: 'Running'
            },
            abnormalCount: {
                type: Number,
                default: 0
            }
        },
        methods: {
            getClass () {
                if (this.status === 'Running') {
                    return 'success';
                }
                if (['Starting', 'Pending'].includes(this.status)) {
                    return 'now';
                }
                return 'failed';
            }
        }
    };
</script>
<style lang="scss">
    .paas-deploy-process-status-item {
        display: inline-block;
        margin-left: 5px;
        min-width: 38px;
        height: 16px;
        line-height: 16px;
        border-radius: 8px;
        text-align: center;
        &.success {
            background: rgba(24, 192, 161, .2);
            color: #18c0a1;
        }
        &.failed {
            background: rgba(234, 54, 54, .2);
            color: #ea3636;
        }
        &.now {
            color: #3a84ff;
            background: rgba(58, 132, 255, .2);
        }
        span {
            display: inherit;
            position: relative;
            top: -1px;
            font-size: 12px;
            transform: scale(0.8);
        }
    }
</style>
