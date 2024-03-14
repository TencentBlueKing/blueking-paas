<template>
  <div :class="['plugin-top-title', { 'no-shadow': !noShadow }]">
    <div class="title-container flex-row align-items-center">
      <i
        v-if="showBackIcon"
        class="paasng-icon paasng-arrows-left icon-cls-back mr5"
        @click="goBack"
      />
      <div class="title">
        {{ title }}
        <span v-if="version">{{ version }}</span>
      </div>
    </div>
  </div>
</template>
<script>import { bus } from '@/common/bus';

export default {
  props: {
    name: {
      type: String,
      default() {
        return '';
      },
    },
    version: {
      type: String,
      default() {
        return '';
      },
    },
    noShadow: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      showBackIcon: false,
    };
  },
  watch: {
    $route: {
      handler(value) {
        if (value) {
          this.title = this.name || (value.meta && value.meta.pathName);
          this.showBackIcon = value.meta && value.meta.supportBack;
        }
      },
      immediate: true,
    },
  },
  methods: {
    goBack() {
      if (this.version) {
        const type = this.$route.query.type || 'prod';
        bus.$emit('stop-deploy', true);
        this.$router.push({
          name: 'pluginVersionManager',
          query: { type },
        });
      } else {
        this.$router.go(-1);
      }
    },
  },
};
</script>
<style lang="scss" scoped>
.plugin-top-title {
  i {
    transform: translateY(0px);
  }
  &.no-shadow {
    height: 52px;
    background: #fff;
    box-shadow: 0 3px 4px 0 #0000000a;
    position: relative;
    padding: 0 24px;
    .title-container .title {
      line-height: 52px;
    }
  }
  .title-container {
    .title {
      font-size: 16px;
      color: #313238;
      letter-spacing: 0;
      line-height: 24px;
    }
    .icon-cls-back {
      color: #3a84ff;
      font-size: 20px;
      font-weight: bold;
      cursor: pointer;
    }
  }
}
</style>
