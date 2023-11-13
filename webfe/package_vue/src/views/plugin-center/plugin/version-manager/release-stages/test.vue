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
    pluginData: {
      type: Object,
      default: () => {},
    },
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
  created() {
    console.log('pluginData', this.pluginData);
    console.log('stageData', this.stageData);
  },
};
</script>

<style lang="scss" scoped>
.testing-container{
  height: calc(100vh - 218px);
  margin-top: 60px;
}

#embed{
    width: 100%;
    height: 100%;
    body::-webkit-scrollbar {
        width: 6px;
        height: 6px;
        background-color: #fafafa;
    }
    body::-webkit-scrollbar-thumb {
        height: 6px;
        border-radius: 4px;
        background-color: #ccc;
    }
}
</style>
