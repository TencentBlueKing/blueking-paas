<template>
  <div class="module-bar-container">
    <div class="title pt15">
      {{ title }}
    </div>
    <bk-tab
      :active.sync="active"
      ext-cls="module-tab-cls"
      type="unborder-card"
      @tab-change="handleTabChange"
    >
      <bk-tab-panel
        v-for="(panel, index) in moduleList"
        :key="index"
        :label="panel.name"
        v-bind="panel"
      />
    </bk-tab>
  </div>
</template>
<script>
import { defineComponent, ref } from '@vue/composition-api';

export default defineComponent({
  name: 'EditorStatus',
  props: {
    title: {
      type: String,
      default: '',
    },
    moduleList: {
      type: Array,
      default() {
        return [];
      },
    },
    curModule: {
      type: Object,
      default() {
        return {
          name: '',
        };
      },
    },
  },
  setup(props) {
    const active = ref(props.curModule.name || '');
    // const { theme } = toRefs(props);
    // const icon = computed(() => {
    //   const iconMap = {
    //     error: 'close-circle-shape',
    //     default: 'info-circle-shape',
    //   };
    //   return iconMap[theme.value] || 'info-circle-shape';
    // });
    const handleTabChange = () => {
      // console.log('active', active);
      // this.isLoading = true;
    };
    return {
      handleTabChange,
      active,
    //   icon,
    };
  },
});
</script>
<style lang="scss" scoped>
    .module-bar-container{
      background: #fff;
        .title{
            font-size: 16px;
            color: #313238;
            padding: 0 24px;
        }
    }
    .module-tab-cls{
      /deep/ .bk-tab-section{
        padding: 0 !important;
      }
    }
</style>
