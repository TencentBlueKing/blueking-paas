<template>
  <div class="module-bar-container">
    <div class="title pt15">
      {{ title }}
    </div>
    <div class="flex-row justify-content-between align-items-center pr40">
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
      <div class="module-manager" @click="handleModuleAdd">
        <i class="icon paasng-icon paasng-gear"></i>
        <span class="pl10">{{ $t('模块管理') }}</span>
      </div>
    </div>

    <bk-dialog
      v-model="dialog.visiable"
      width="640"
      :theme="'primary'"
      :header-position="'left'"
      :show-footer="false"
      :mask-close="true"
      :title="dialog.title"
      :loading="dialog.loading"
    >
      <bk-button
        theme="primary"
        @click="handleToAddModulePage">
        <i class="paasng-icon paasng-plus-thick add-icon" />
        {{ $t('新增模块') }}
      </bk-button>

      <div
        class="module-item flex-row justify-content-between align-items-center"
        :class="[index === moduleItemIndex ? 'module-item-active' : '']"
        v-for="(panel, index) in moduleList"
        :key="index"
        @mouseenter="handleMouseEnter(index)"
        @mouseleave="moduleItemIndex = ''">
        {{ panel.name }}
        <i v-if="index === moduleItemIndex" class="icon paasng-icon paasng-delete delete-module-icon"></i>
      </div>
    </bk-dialog>
  </div>
</template>
<script>
import { defineComponent, reactive, ref } from 'vue';
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
    const moduleItemIndex = ref('');
    const dialog = reactive({
      title: '模块管理',
      visiable: false,
      loading: false,
    });
    // 切换tab
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

    // 模块管理
    const handleModuleAdd = () => {
      dialog.visiable = true;
    };

    const handleToAddModulePage = () => {
      router.push({
        name: 'appCreateModule',
        params: {
          id: route.params.id,
        },
      });
    };

    const handleMouseEnter = (index) => {
      moduleItemIndex.value = index;
    };

    return {
      handleTabChange,
      handleModuleAdd,
      handleToAddModulePage,
      handleMouseEnter,
      active,
      dialog,
      moduleItemIndex,
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
    .module-manager{
      color: #3A84FF;
      cursor: pointer;
    }

    .module-item{
      width: 592px;
      height: 40px;
      background: #FAFBFD;
      border: 1px solid #DCDEE5;
      border-radius: 2px;
      padding: 0 20px;
      margin-top: 20px;
      cursor: pointer;
      .delete-module-icon{
        color: #EA3636;
        font-size: 16px;
      }
    }
    .module-item-active{
      background: #F0F1F5;
    }
</style>
