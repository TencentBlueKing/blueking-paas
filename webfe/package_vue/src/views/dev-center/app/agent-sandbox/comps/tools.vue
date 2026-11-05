<template>
  <div>
    <access-guide
      v-if="activePanel === 'guide'"
      :key="`guide-${appCode}`"
      :app-code="appCode"
      :template-id.sync="templateId"
      @close="close"
      @api-keys="openKeys"
    />
    <api-keys
      v-if="activePanel === 'keys'"
      :key="`keys-${appCode}`"
      :app-code="appCode"
      :show-guide="returnToGuide"
      @close="close"
      @guide="activePanel = 'guide'"
    />
  </div>
</template>

<script>
import AccessGuide from './access-guide.vue';
import ApiKeys from './api-keys.vue';

export default {
  name: 'SandboxTools',
  components: { AccessGuide, ApiKeys },
  props: {
    appCode: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      activePanel: '',
      templateId: '',
      returnToGuide: false,
    };
  },
  watch: {
    appCode: 'close',
    '$route.fullPath': 'close',
  },
  methods: {
    openGuide(templateId = '') {
      this.templateId = templateId;
      this.returnToGuide = false;
      this.activePanel = 'guide';
    },
    openKeys() {
      this.returnToGuide = this.activePanel === 'guide';
      this.activePanel = 'keys';
    },
    close() {
      this.activePanel = '';
      this.templateId = '';
      this.returnToGuide = false;
    },
  },
};
</script>
