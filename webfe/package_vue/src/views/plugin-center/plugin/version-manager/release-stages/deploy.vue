<template>
  <!-- 部署模块 -->
  <div class="plugin-container">
    <div
      class="wrapper primary
                            release-info-box
                            flex-row
                            justify-content-between
                            align-items-center"
      :class="[{ 'failed': status === 'failed' }, { 'success': status === 'successful' }]"
    >
      <div
        v-if="status === 'pending'"
        class="info-left-warp flex-row"
      >
        <round-loading
          size="small"
          ext-cls="deploy-round-loading"
        />
        <span class="info-time pl10">
          <span class="info-pending-text"> {{ $t('正在部署中...') }} </span>
          <!-- <span class="time-text"> {{ $t('耗时：') }} 13秒</span> -->
        </span>
      </div>
      <div
        v-else-if="status === 'failed'"
        class="error-left-warp flex-row align-items-center"
      >
        <i class="error-icon paasng-icon paasng-close-circle-shape" />
        <span class="info-time pl10">
          <span class="info-pending-text"> {{ $t('构建失败') }} </span>
          <span class="time-text">{{ stageData.failedMessage }}</span>
        </span>
      </div>
      <div
        v-else-if="status === 'successful'"
        class="info-left-warp flex-row"
      >
        <span class="success-check-wrapper">
          <i class="paasng-icon paasng-correct" />
        </span>
        <span class="info-time pl10">
          <span class="info-pending-text"> {{ $t('部署成功') }} </span>
        </span>
      </div>
      <div
        v-if="status !== 'successful'"
        class="info-right-warp"
      >
        <bk-button
          v-if="status !== 'pending'"
          size="small"
          theme="primary"
          :outline="true"
          :class="[{ 'failed': status === 'failed' }]"
          class="ext-cls-btn"
          @click="clickRerun(status)"
        >
          {{ $t('重新部署') }}
        </bk-button>
      </div>
    </div>
    <div
      id="release-box"
      class="release-warp"
    >
      <div class="release-log-warp flex-row">
        <div
          id="release-timeline-box"
          style="width: 230px;padding-left: 8px;"
        >
          <release-timeline
            ref="deployTimelineRef"
            :list="steps"
          />
        </div>
        <release-log
          ref="deployLogRef"
          :log="logs"
        />
      </div>
    </div>
  </div>
</template>
<script>
    import pluginBaseMixin from '@/mixins/plugin-base-mixin';
    import releaseTimeline from './comps/release-timeline';
    import releaseLog from './comps/release-log.vue';
    import stageBaseMixin from './stage-base-mixin';

    export default {
        components: {
            releaseTimeline,
            releaseLog
        },
        mixins: [stageBaseMixin, pluginBaseMixin],
        props: {
            stageData: {
                type: Object,
                default: () => {}
            }
        },
        data: function () {
          return {
            winHeight: 300,
            logs: [],
            steps: [],
            status: ''
          };
        },
        computed: {
            releaseId () {
                return this.$route.query.release_id;
            }
        },
        watch: {
            stageData: {
                handler (newStageData) {
                    this.logs = newStageData.detail.logs;
                    this.steps = this.modifyDeployStepsData(newStageData.detail.steps);
                    this.status = newStageData.status;
                },
                deep: true,
                immediate: true
            }
        },
        methods: {
          getDisplayTime (payload) {
                let theTime = payload;
                if (theTime < 1) {
                    return `< 1${this.$t('秒')}`;
                }
                let middle = 0;
                let hour = 0;

                if (theTime > 60) {
                    middle = parseInt(theTime / 60, 10);
                    theTime = parseInt(theTime % 60, 10);
                    if (middle > 60) {
                        hour = parseInt(middle / 60, 10);
                        middle = parseInt(middle % 60, 10);
                    }
                }

                let result = '';

                if (theTime > 0) {
                    result = `${theTime}${this.$t('秒')}`;
                }
                if (middle > 0) {
                    result = `${middle}${this.$t('分')}${result}`;
                }
                if (hour > 0) {
                    result = `${hour}${this.$t('时')}${result}`;
                }

                return result;
            },

            /**
             * 计算部署进程间的所花时间
             */
             computedDeployTime (startTime, endTime) {
                const start = new Date(startTime).getTime();
                const end = new Date(endTime).getTime();
                const interval = (end - start) / 1000;

                if (!interval) {
                    return `< 1${this.$t('秒')}`;
                }

                return this.getDisplayTime(interval);
            },

            modifyDeployStepsData (steps) {
                return steps.map(item => {
                    // da根据 steps[i].status 来决定当前部署的状态
                    item.time = this.computedDeployTime(item.start_time, item.complete_time);
                    if (item.status === 'successful' || item.status === 'failed') {
                        item.tag = `
                        <div style="width: 185px" class="flex-row justify-content-between">
                            <div>${item.name}</div>
                            <div style="color: #C4C6CC" class="time-cls">${item.time}</div>
                        </div>
                        `;
                    } else {
                        item.tag = `
                        <div style="width: 185px" class="flex-row justify-content-between">
                            <div>${item.name}</div>
                        </div>
                        `;
                    }
                    switch (item.status) {
                        case 'successful':
                            item.type = 'success';
                            break;
                        case 'failed':
                            item.type = 'danger';
                            break;
                        case 'pending':
                            item.type = 'primary';
                            item.icon = <round-loading size="small" ext-cls="deploy-round-loading" />;
                            break;
                    }
                    return item;
                });
            },
            clickRerun (status) {
                if (status !== 'pending') {
                    this.$emit('rerunStage');
                }
            }
        }
    };
</script>
