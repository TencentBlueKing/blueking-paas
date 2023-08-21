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
import { defineComponent, ref } from 'vue';
import store from '@/store';
import router from '@/router';

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
    const route = router.currentRoute;
    const active = ref(props.curModule.name || '');
    const handleTabChange = () => {
      const curModule = (props.moduleList || []).find(e => e.name === active.value);
      store.commit('updateCurAppModule', curModule);

      const { name } = route;
      let { query } = route;
      if (name === 'appLog') {
        query = {
          tab: route.query.tab || '',
        };
      }

      router.push({
        name,
        params: {
          id: route.params.id,
          moduleId: curModule.name,
        },
        query,
      });
    };
    return {
      handleTabChange,
      active,
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
