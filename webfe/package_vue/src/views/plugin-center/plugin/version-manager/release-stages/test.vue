<template>
  <div class="testing-container">
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
<script>
import stageBaseMixin from './stage-base-mixin';

export default {
  mixins: [stageBaseMixin],
  props: {
    stageData: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      testingPhaseURL: '',
    };
  },
  computed: {
    testPageUrl() {
      return this.stageData.detail?.page_url;
    },
  },
};
</script>

<style lang="scss" scoped>
.testing-container {
  height: calc(100vh - 194px);

  /* resize and min-height are optional, allows user to resize viewable area */
  -webkit-resize: vertical;
  -moz-resize: vertical;
  resize: vertical;
  min-height: 317px;
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
