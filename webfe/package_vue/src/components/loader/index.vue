<template lang="html">
  <div
    :class="[{ 'paas-loading-content': isLoaderShow, loading: localLoading, fadeout: !localLoading }]"
    :style="styleObject"
  >
    <div
      :class="[
        'loading-placeholder',
        { hide: !isLoaderShow },
        { transition: !isTransition },
        { 'customize-width': isCustomizeWidth },
      ]"
      :style="{ 'background-color': backgroundColor }"
    >
      <template v-if="isLoaderShow && loaderComponent">
        <component
          :key="loaderRenderKey"
          :is="loaderComponent"
          :style="{ 'padding-top': `${offsetTop}px`, 'margin-left': `${offsetLeft}px`, 'transform-origin': 'left' }"
          :base-width="baseWidth"
          :content-width="contentWidth"
          :is-transform="isTransform"
          v-bind="resolvedLoaderProps"
        />
      </template>
    </div>
    <slot />
  </div>
</template>

<script>
import loadingMap from './loading-map';

export default {
  props: {
    isLoading: {
      type: Boolean,
      default: false,
    },
    placeholder: {
      type: String,
    },
    offsetTop: {
      type: [Number, String],
      default: 25,
    },
    offsetLeft: {
      type: [Number, String],
      default: 0,
    },
    height: {
      type: Number,
    },
    delay: {
      type: Number,
      default: 300,
    },
    backgroundColor: {
      type: String,
      default: '#FFF',
    },
    isTransition: {
      type: Boolean,
      default: true,
    },
    isTransform: {
      type: Boolean,
      default: true,
    },
    isCustomizeWidth: {
      type: Boolean,
      default: false,
    },
    isMinHeight: {
      type: Boolean,
      default: true,
    },
    customStyle: {
      type: Object,
      default: () => ({}),
    },
    loaderProps: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      localLoading: this.isLoading,
      isLoaderShow: this.isLoading,
      baseWidth: 1180,
      contentWidth: 1180,
      curPlaceholder: '',
      isPlugin: false,
      closeLoadingTimer: null,
      hideLoaderTimer: null,
    };
  },
  computed: {
    loaderDefinition() {
      if (!this.placeholder) {
        return null;
      }
      return loadingMap[this.placeholder] || { component: this.placeholder };
    },
    loaderComponent() {
      if (!this.loaderDefinition) {
        return null;
      }
      return this.loaderDefinition.component || this.loaderDefinition;
    },
    resolvedLoaderProps() {
      const presetProps = this.loaderDefinition && this.loaderDefinition.props ? this.loaderDefinition.props : {};
      return {
        ...presetProps,
        ...this.loaderProps,
      };
    },
    loaderRenderKey() {
      return `${this.placeholder || 'loader'}-${this.baseWidth}-${this.contentWidth}`;
    },
    styleObject() {
      return { ...this.customStyle };
    },
  },
  watch: {
    isLoading(newVal, oldVal) {
      this.clearLoadingTimers();

      if (oldVal && !newVal) {
        this.closeLoadingTimer = setTimeout(() => {
          this.localLoading = this.isLoading;
          this.hideLoaderTimer = setTimeout(() => {
            this.isLoaderShow = this.isLoading;
          }, 200);
        }, this.delay);
      } else {
        this.localLoading = this.isLoading;
        this.isLoaderShow = this.isLoading;
      }
    },
    $route: {
      handler(value) {
        this.isPlugin = value.path.includes('/plugin-center');
      },
      immediate: true,
    },
  },
  created() {
    this.initContentWidth();
  },
  mounted() {
    if (this.isPlugin) {
      this.baseWidth = 1680;
      this.contentWidth = 2450;
    } else {
      this.initContentWidth();
      window.addEventListener('resize', this.initContentWidth);
    }
  },
  beforeDestroy() {
    this.clearLoadingTimers();
    window.removeEventListener('resize', this.initContentWidth);
  },
  methods: {
    clearLoadingTimers() {
      clearTimeout(this.closeLoadingTimer);
      clearTimeout(this.hideLoaderTimer);
      this.closeLoadingTimer = null;
      this.hideLoaderTimer = null;
    },
    initContentWidth() {
      const winWidth = window.innerWidth;
      if (winWidth < 1440) {
        this.baseWidth = 1180;
        this.contentWidth = 980;
      } else if (winWidth < 1680) {
        this.baseWidth = 1180;
        this.contentWidth = 1080;
      } else if (winWidth < 1920) {
        this.baseWidth = 1180;
        this.contentWidth = 1180;
      } else {
        this.baseWidth = 1440;
        this.contentWidth = 1440;
      }
      this.contentWidth = Math.max(this.contentWidth, this.baseWidth);
    },
  },
};
</script>

<style lang="scss">
.paas-loading-content {
  position: relative;
  overflow: hidden;
  height: 100%;

  &.loading {
    * {
      opacity: 0 !important;
    }
  }

  &.fadeout {
    .loading-placeholder {
      opacity: 0 !important;
    }
  }

  .loading-placeholder {
    opacity: 1 !important;
    position: absolute;
    width: 100%;
    height: 100%;
    left: 0;
    right: 0;
    top: 0;
    bottom: 0;
    z-index: 100;
    transition: opacity ease 0.5s;
    padding: 0 24px;
    margin-top: 14px;

    &.hide {
      z-index: -1;
    }

    &.transition {
      transition: none;
    }

    svg {
      width: 1180px;
    }

    * {
      opacity: 1 !important;
    }
  }
}

@media (min-width: 1280px) {
  .paas-loading-content .loading-placeholder {
    width: auto;
    svg {
      width: 100%;
    }
    &.customize-width {
      svg {
        width: calc(100% - 48px);
      }
    }
  }
}
@media screen and (min-width: 1680px) {
}
@media screen and (min-width: 1920px) {
}
@media screen and (min-width: 2450px) {
  .paas-loading-content .loading-placeholder {
    width: auto;
    svg {
      width: 100%;
    }
  }
}
.hide {
  display: none;
}
</style>
