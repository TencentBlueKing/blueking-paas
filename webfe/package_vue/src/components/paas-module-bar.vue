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

      <bk-alert class="mb20" type="error" :title="$t('删除操作无法撤回，请在删除前与应用其他成员沟通')"></bk-alert>
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
        <i
          v-if="index === moduleItemIndex" class="icon paasng-icon paasng-delete delete-module-icon"
          @click="handleDeleteModule(panel)"></i>
      </div>
    </bk-dialog>


    <bk-dialog
      v-model="delAppDialog.visiable"
      width="540"
      :title="`${$t('确认删除模块')}【${curAppModuleName.value}】？`"
      :theme="'primary'"
      :mask-close="false"
      :loading="delAppDialog.isLoading"
      @after-leave="hookAfterClose"
    >
      <div class="ps-form">
        <div class="spacing-x1">
          {{ $t('请完整输入') }} <code>{{ curAppModuleName }}</code> {{ $t('来确认删除模块！') }}
        </div>
        <div class="ps-form-group">
          <input
            v-model="formRemoveConfirmCode"
            type="text"
            class="ps-form-control"
          >
        </div>
      </div>
      <div slot="footer">
        <bk-button
          theme="primary"
          :disabled="!formRemoveValidated"
          @click="submitRemoveModule"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          theme="default"
          @click="delAppDialog.visiable = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>
  </div>
</template>
<script>import { defineComponent, reactive, ref, computed, getCurrentInstance } from 'vue';
import store from '@/store';
import router from '@/router';
import { bkMessage } from 'bk-magic-vue';

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
    const vm = getCurrentInstance();
    const active = ref(props.curModule.name || '');
    const moduleItemIndex = ref('');
    const formRemoveConfirmCode = ref('');
    const curAppModuleName = ref('');
    const dialog = reactive({
      title: '模块管理',
      visiable: false,
      loading: false,
    });
    const delAppDialog = reactive({
      visiable: false,
      isLoading: false,
    });

    // 输入的文案和选中模块相同
    const formRemoveValidated = computed(() => curAppModuleName.value === formRemoveConfirmCode.value);
    const appCode = computed(() => route.params.id);

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
          id: appCode.value,
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
          id: appCode.value,
        },
      });
    };

    const handleMouseEnter = (index) => {
      moduleItemIndex.value = index;
    };

    const handleDeleteModule = (payload) => {
      curAppModuleName.value = payload.name;
      delAppDialog.visiable = true;
      dialog.visiable = false;
    };

    const submitRemoveModule = async () => {
      try {
        await store.dispatch('module/deleteModule', {
          appCode: appCode.value,
          moduleName: curAppModuleName.value,
        });
        console.log('vue', vm);
        bkMessage({
          theme: 'success',
          message: '模块删除成功',
        });
        router.push({
          name: 'appSummary',
          params: {
            id: appCode.value,
            moduleId: props.moduleList.find(item => item.is_default).name,
          },
        });
        store.dispatch('getAppInfo', { appCode: appCode.value, moduleId: curAppModuleName.value });
      } catch (res) {
        console.warn(res);
        bkMessage({
          theme: 'error',
          message: res.message,
        });
      } finally {
        delAppDialog.visiable = false;
      }
    };

    const hookAfterClose = () => {
      formRemoveConfirmCode.value = '';
    };

    return {
      handleTabChange,
      handleModuleAdd,
      handleToAddModulePage,
      handleMouseEnter,
      active,
      dialog,
      delAppDialog,
      moduleItemIndex,
      handleDeleteModule,
      formRemoveValidated,
      submitRemoveModule,
      hookAfterClose,
      curAppModuleName,
      formRemoveConfirmCode,
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
