<template lang="html">
  <!-- 普通应用 -->
  <default-overview v-if="isEngineless" />
  <!-- 外链应用 -->
  <engineless-overview v-else />
</template>

<script>
    import defaultOverview from './default-overview.vue';
    import enginelessOverview from './engineless-overview.vue';
    export default {
        components: {
            defaultOverview,
            enginelessOverview
        },
        computed: {
            curAppInfo () {
                return this.$store.state.curAppInfo;
            },
            isEngineless () {
                return this.curAppInfo.web_config.engine_enabled;
            }
        }
    };
</script>
