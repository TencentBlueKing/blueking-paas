<template lang="html">
  <div class="right-main">
    <div class="overview-tit">
      <h2>403</h2>
    </div>
    <div
      class="log-middle"
      style="width: 1180px; margin: 0 auto; padding-bottom: 0"
    >
      <div
        class="nofound"
        style="width: 1180px; margin: 0 auto;"
      >
        <img src="/static/images/permissions.png">
        <p> {{ $t('您没有访问当前应用该功能的权限') }} </p>
        <a
          v-if="applyUrl"
          :href="applyUrl"
          target="blank"
        >
          <bk-button
            :theme="'primary'"
            :title="$t('申请成为开发者')"
            class="mr10"
          >
            {{ $t('申请成为开发者') }}
          </bk-button>
        </a>
      </div>
    </div>
  </div>
</template>

<script>
    export default {
        computed: {
            isPlugin () {
                  return this.$route.meta.plugin;
            },
            applyUrl () {
                if (this.isPlugin) {
                    return this.$store.state.plugin.pluginApplyUrl;
                }
                return this.$store.state.applyUrl;
            },
            id () {
                return this.$route.params.id;
            },
            pluginTypeId () {
                return this.$route.params.pluginTypeId;
            }
        },
        async created () {
            if (!this.applyUrl) {
                if (this.isPlugin) {
                    await this.$store.dispatch('plugin/getPluginInfo', { pluginId: this.id, pluginTypeId: this.pluginTypeId });
                } else {
                    await this.$store.dispatch('getAppInfo', { appCode: this.id });
                }
            }
        }
    };
</script>

<style lang="css" scoped>
    .nofound {
        width: 939px;
        padding-top: 150px;
        text-align: center;
    }

    .nofound p {
        font-size: 20px;
        color: #979797;
        line-height: 80px;
    }
</style>
