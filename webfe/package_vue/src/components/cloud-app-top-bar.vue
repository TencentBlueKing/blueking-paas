<template>
  <div class="nav-wrapper">
    <div class="title pt15">
      {{ title }}
    </div>
    <div class="flex-row justify-content-between align-items-center">
      <bk-tab
        :active.sync="curActive"
        ext-cls="app-tab-cls"
        type="unborder-card"
        @tab-change="handleTabChange"
      >
        <bk-tab-panel
          v-for="(panel, index) in navList"
          :key="index"
          :label="panel.label"
          v-bind="panel"
        />
      </bk-tab>
      <div class="module-manager" @click="handleRightConfigClick">
        <i class="paasng-icon paasng-lishijilu"></i>
        <span class="title">{{ rightTitle }}</span>
      </div>
    </div>
  </div>
</template>
<script>
import { defineComponent, ref } from 'vue';

export default defineComponent({
  name: 'EditorStatus',
  props: {
    title: {
      type: String,
      default: '',
    },
    navList: {
      type: Array,
      default() {
        return [];
      },
    },
    active: {
      type: String,
      default: ''
    },
    rightTitle: {
      type: String,
      default: ''
    }
  },
  setup(props, { emit }) {
    const curActive = ref(props.active || props.navList[0]?.name);

    const handleTabChange = () => {
      emit('change', curActive.value);
    };

    const handleRightConfigClick = () => {
      emit('right-config-click');
    }

    return {
      curActive,
      handleTabChange,
      handleRightConfigClick
    };
  },
});
</script>
<style lang="scss" scoped>
    .nav-wrapper{
      background: #fff;
        .title{
            font-size: 16px;
            color: #313238;
            padding: 0 24px;
        }
    }
    .app-tab-cls{
      /deep/ .bk-tab-section{
        padding: 0 !important;
      }
    }
    .module-manager{
      color: #3A84FF;
      cursor: pointer;

      .title {
        font-size: 14px;
        color: #3A84FF;
        padding-left: 6px;
      }
    }
</style>
