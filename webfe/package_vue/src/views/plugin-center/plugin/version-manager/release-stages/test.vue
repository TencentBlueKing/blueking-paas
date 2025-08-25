<template>
  <div :class="['testing-container', { 'hide-button-group': !isBottomActionBar }]">
    <!-- scrolling 是否显示滚动条 -->
    <!-- frameborder 是否显示边框 -->
    <iframe
      id="embed"
      :src="testPageUrl"
      scrolling="no"
      frameborder="0"
    />
  </div>
</template>
<script>import stageBaseMixin from './stage-base-mixin';

export default {
  mixins: [stageBaseMixin],
  props: {
    stageData: {
      type: Object,
      default: () => {},
    },
    manualPreview: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      testingPhaseURL: '',
    };
  },
  computed: {
    testPageUrl() {
      // 手动预览 mode=read
      if (this.manualPreview) {
        return this.stageData.detail?.page_url.replace(/mode=edit/, 'mode=read');
      }
      return this.stageData.detail?.page_url;
    },
    // 是否存在底部操作栏
    isBottomActionBar() {
      return document.querySelector('.footer-btn-warp');
    },
  },
  created() {
    window.addEventListener('message', this.messageEvent);

    // 组件销毁前
    this.$once('hook:beforeDestroy', () => {
      window.removeEventListener('message', this.messageEvent);
    });
  },
  methods: {
    messageEvent(event) {
      if (event.data && event.data.type === 'udcTaskDelete') {
        this.$bkMessage({
          theme: 'success',
          message: this.$t('取消成功'),
        });
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.testing-container {
  flex: 1;
  margin-bottom: 48px;

  /* resize and min-height are optional, allows user to resize viewable area */
  -webkit-resize: vertical;
  -moz-resize: vertical;
  resize: vertical;
  min-height: 317px;

  &.hide-button-group {
    margin-bottom: 24px;
  }
}

iframe#embed {
  width: 100%;
  height: 100%;

  /* resize seems to inherit in at least Firefox */
  -webkit-resize:none;
  -moz-resize:none;
  resize:none;
}
</style>
