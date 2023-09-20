<template>
  <div class="module-bar-container">
    <div class="title pt15">
      {{ title }}
    </div>
    <div class="flex-row align-items-center pr40">
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
      <div class="module-operate">
        <!-- 新增模块 -->
        <div
          class="icon-warapper"
          :title="$t('新增模块')"
          @click="handleToAddModulePage"
        >
          <i class="paasng-icon paasng-plus"></i>
        </div>
        <!-- 模块管理 -->
        <div
          class="icon-warapper"
          :title="$t('模块管理')"
          @click="handleModuleAdd"
        >
          <i class="icon paasng-icon paasng-gear"></i>
        </div>
      </div>
    </div>

    <bk-dialog
      v-model="dialog.visiable"
      width="640"
      :theme="'primary'"
      :header-position="'left'"
      :show-footer="false"
      :mask-close="true"
      :title="$t(dialog.title)"
      :loading="dialog.loading"
    >
      <bk-alert
        class="mb20"
        type="error"
        :title="$t('删除操作无法撤回，请在删除前与应用其他成员沟通')"
      ></bk-alert>
      <bk-button
        theme="primary"
        @click="handleToAddModulePage"
      >
        <i class="paasng-icon paasng-plus-thick add-icon" />
        {{ $t('新增模块') }}
      </bk-button>

      <div
        class="module-item flex-row justify-content-between align-items-center"
        :class="[index === moduleItemIndex ? 'module-item-active' : '']"
        v-for="(panel, index) in moduleList"
        :key="index"
        @mouseenter="handleMouseEnter(index)"
        @mouseleave="moduleItemIndex = ''"
      >
        {{ panel.name }}
        <i
          v-if="index === moduleItemIndex && !panel.is_default"
          class="icon paasng-icon paasng-delete delete-module-icon"
          @click="handleDeleteModule(panel)"
        ></i>
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="delAppDialog.visiable"
      width="540"
      :title="`${$t('确认删除模块')}【${curAppModuleName}】？`"
      :theme="'primary'"
      :mask-close="false"
      :loading="delAppDialog.isLoading"
      @after-leave="hookAfterClose"
    >
      <div class="ps-form">
        <div class="spacing-x1">
          {{ $t('请完整输入') }}
          <code>{{ curAppModuleName }}</code>
          {{ $t('来确认删除模块！') }}
        </div>
        <div class="ps-form-group">
          <input
            v-model="formRemoveConfirmCode"
            type="text"
            class="ps-form-control"
          />
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
<script>
import { defineComponent, reactive, ref, computed, getCurrentInstance } from 'vue';
import store from '@/store';
import router from '@/router';
import { bkMessage } from 'bk-magic-vue';

export default defineComponent({
  name: 'EditorStatus',
  props: {
    appCode: {
      type: String | Number,
    },
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
    firstModuleName: {
      type: String,
      default: '',
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

    // 切换tab
    const handleTabChange = async () => {
      const curModule = (props.moduleList || []).find(e => e.name === active.value);
      await store.commit('updateCurAppModule', curModule);

      const name = props.firstModuleName || route.name;
      let { query } = route;
      if (name === 'appLog') {
        query = {
          tab: route.query.tab || '',
        };
      }

      router.push({
        name,
        params: {
          id: props.appCode,
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
          id: props.appCode,
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
      3;
      try {
        await store.dispatch('module/deleteModule', {
          appCode: props.appCode,
          moduleName: curAppModuleName.value,
        });
        console.log('vue', vm);
        bkMessage({
          theme: 'success',
          message: '模块删除成功',
        });
        await store.dispatch('getAppInfo', {
          appCode: props.appCode,
          moduleId: props.moduleList.find(item => item.is_default).name,
        });
        router.push({
          name: props.firstModuleName || route.name,
          params: {
            id: props.appCode,
            moduleId: props.moduleList.find(item => item.is_default).name,
          },
        });
        store.dispatch('getAppInfo', { appCode: props.appCode, moduleId: curAppModuleName.value });
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
.module-bar-container {
  background: #fff;
  box-shadow: 0 3px 4px 0 #0000000a;
  .title {
    font-size: 16px;
    color: #313238;
    padding: 0 24px;
  }
}
.module-tab-cls {
  /deep/ .bk-tab-section {
    padding: 0 !important;
  }
  /deep/ .bk-tab-header {
    background-image: none !important;
  }
}
.module-manager {
  color: #3a84ff;
  cursor: pointer;
}

.module-operate {
  position: sticky;
  right: 20px;
  background: #fff;
  padding: 12px 0 12px 12px;
  display: flex;
  .icon-warapper {
    width: 26px;
    height: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #F0F5FF;
    border-radius: 2px;
    cursor: pointer;
    i {
      line-height: 26px;
      color: #3a84ff;
    }
    &:first-child {
      margin-right: 8px;
      i {
        font-weight: 700;
        font-size: 12px;
      }
    }
  }
}

.module-item {
  width: 592px;
  height: 40px;
  background: #fafbfd;
  border: 1px solid #dcdee5;
  border-radius: 2px;
  padding: 0 20px;
  margin-top: 20px;
  cursor: pointer;
  .delete-module-icon {
    color: #ea3636;
    font-size: 16px;
  }
}
.module-item-active {
  background: #f0f1f5;
}
</style>
