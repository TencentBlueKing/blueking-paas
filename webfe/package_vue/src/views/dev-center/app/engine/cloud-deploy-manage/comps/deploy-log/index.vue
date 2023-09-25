<template>
  <div class="paas-deploy-log-wrapper">
    <stage-item
      v-if="isShowReady"
      ref="readyStageRef"
      :title="$t('准备阶段')"
      :data="readyList"
    />
    <stage-item
      v-if="isShowBuild"
      ref="buildStageRef"
      :title="$t('构建阶段')"
      can-full-screen
      :data="buildList"
      style="margin-top: 8px;"
    />
    <deploy-stage-item
      v-if="isShowRelease"
      ref="nowStageRef"
      :loading="processLoading"
      :data="processList"
      style="margin-top: 8px;"
      :environment="environment"
    />
    <skip-stage-item
      v-if="isShowSkip"
      style="margin-top: 8px;"
    />
  </div>
</template>
<script>
import StageItem from './render-stage';
import SkipStageItem from './render-skip-stage';
import DeployStageItem from './deploy-stage';
export default {
  name: '',
  components: {
    StageItem,
    SkipStageItem,
    DeployStageItem,
  },
  props: {
    readyList: {
      type: Array,
      default: () => [],
    },
    buildList: {
      type: Array,
      default: () => [],
    },
    processList: {
      type: Array,
      default: () => [],
    },
    stateProcess: {
      type: Array,
      default: () => [],
    },
    isShowSkip: {
      type: Boolean,
      default: false,
    },
    // 部署阶段获取部署进程的loading
    processLoading: {
      type: Boolean,
      default: false,
    },
    environment: {
      type: String,
      default: 'stag',
    },
  },
  data() {
    return {};
  },
  computed: {
    isShowReady() {
      return this.stateProcess.includes('preparation');
    },
    isShowBuild() {
      return this.stateProcess.includes('build');
    },
    isShowRelease() {
      return this.stateProcess.includes('release');
    },
  },
  watch: {
    buildList: {
      handler() {
        this.$nextTick(() => {
          this.$refs.buildStageRef && this.$refs.buildStageRef.handleScrollToBottom();
        });
      },
      immediate: true,
    },
  },
  methods: {
    handleScrollToLocation(type) {
      const $dom = document.querySelector('.paas-deploy-log-wrapper');
      if (type === 'preparation') {
        $dom.scrollTo(0, 0);
        return;
      }
      if (type === 'release') {
        const $ref = this.$refs.nowStageRef;
        const distance = $ref.$el.offsetTop || 0;
        $dom.scrollTo(0, distance);
      }
    },
  },
};
</script>
<style lang="scss">
    .paas-deploy-log-wrapper {
        margin-left: 20px;
        padding: 17px 30px;
        width: calc(100% - 250px);
        height: 670px;
        background: #313238;
        overflow-y: auto;
        &::-webkit-scrollbar {
            width: 4px;
            background-color: lighten(transparent, 80%);
        }
        &::-webkit-scrollbar-thumb {
            height: 5px;
            border-radius: 2px;
            background-color: #63656e;
        }
    }
</style>
