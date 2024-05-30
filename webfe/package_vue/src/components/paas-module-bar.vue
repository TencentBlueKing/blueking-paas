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
          v-bk-tooltips="{ content: $t(disableTips), disabled: isCreatedModule }"
          class="icon-warapper mr8"
          :class="{ disabled: !isCreatedModule }"
          :title="$t('新增模块')"
          @click="handleToAddCloudModulePage"
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
        :title="$t('主模块不能删除，删除操作无法撤回，请在删除前与应用其他成员沟通')"
      ></bk-alert>
      <span v-bk-tooltips="{ content: $t(disableTips), disabled: isCreatedModule }">
        <bk-button
          theme="primary"
          :disabled="!isCreatedModule"
          @click="handleToAddCloudModulePage"
        >
          <i class="paasng-icon paasng-plus-thick add-icon" />
          {{ $t('新增模块') }}
        </bk-button>
      </span>

      <div
        class="module-item flex-row justify-content-between align-items-center"
        :class="[index === moduleItemIndex ? 'module-item-active' : '']"
        v-for="(panel, index) in moduleList"
        :key="index"
        @mouseenter="handleMouseEnter(index)"
        @mouseleave="moduleItemIndex = ''"
      >
        <div class="module-name">
          {{ panel.name }}
          <img
            v-if="panel.is_default"
            :class="['module-default', 'ml10', { en: localLanguage === 'en' }]"
            :src="`/static/images/${localLanguage === 'en' ? 'main_en.png' : 'main.png' }`"
          >
        </div>
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
          :loading="delAppDialog.isLoading"
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
import { bus } from '@/common/bus';
import i18n from '@/language/i18n';

export default defineComponent({
  name: 'EditorStatus',
  props: {
    appCode: {
      // eslint-disable-next-line vue/require-prop-type-constructor
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
    activeRouteName: {
      type: String,
      default: '',
    },
  },
  setup(props, { emit }) {
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
    const { curAppInfo, curAppModule } = store.state;

    bus.$on('cloud-change-module', (data) => {
      active.value = data.params.moduleId;
      // 切换路由至该服务的分享模块
      router.push(data);
    });

    // 输入的文案和选中模块相同
    const formRemoveValidated = computed(() => curAppModuleName.value === formRemoveConfirmCode.value);

    // 当前语言
    const localLanguage = computed(() => store.state.localLanguage);

    // 是否展示新建模块入口
    const isCreatedModule = computed(() => curAppInfo.application?.config_info?.can_create_extra_modules);

    const isSmartApp = computed(() => curAppModule.source_origin === vm.proxy.GLOBAL.APP_TYPES.SMART_APP);

    // 新建模块禁用提示
    const disableTips = computed(() => (isSmartApp.value ? i18n.t('S-mart 应用不允许在页面上新建模块') : i18n.t('当前应用不允许创建其他模块')));

    // 切换tab
    const handleTabChange = async () => {
      const curModule = (props.moduleList || []).find(e => e.name === active.value);
      await store.commit('updateCurAppModule', curModule);
      emit('tab-change');
      const name = props.activeRouteName || props.firstModuleName;
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

    // 新增云原生应用模块
    const handleToAddCloudModulePage = () => {
      if (!isCreatedModule.value) {
        return;
      }
      router.push({
        name: 'appCreateCloudModule',
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
      delAppDialog.isLoading = true;
      try {
        await store.dispatch('module/deleteModule', {
          appCode: props.appCode,
          moduleName: curAppModuleName.value,
        });
        bkMessage({
          theme: 'success',
          message: i18n.t('模块删除成功'),
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
        delAppDialog.isLoading = false;
      }
    };

    const hookAfterClose = () => {
      formRemoveConfirmCode.value = '';
    };

    return {
      handleTabChange,
      handleModuleAdd,
      handleToAddCloudModulePage,
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
      localLanguage,
      isCreatedModule,
      disableTips,
    };
  },
});
</script>
<style lang="scss" scoped>
.module-bar-container {
  position: relative;
  z-index: 999;
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
      color: #3a84ff;
    }
    i.paasng-plus {
      font-weight: 700;
      font-size: 12px;
    }
    &.disabled  {
      background: #F5F7FA;
      cursor: not-allowed;
      i {
        color: #DCDEE5;
      }
    }
  }
  .mr8 {
    margin-right: 8px;
  }
}

.module-item {
  width: 592px;
  height: 40px;
  background: #FAFBFD;
  border: 1px solid #DCDEE5;
  border-radius: 2px;
  padding: 0 20px;
  margin-top: 12px;
  cursor: pointer;
  .delete-module-icon {
    color: #ea3636;
    font-size: 16px;
  }
}
.module-item-active {
  background: #f0f1f5;
}
.module-name {
  display: flex;
  align-items: center;
  .module-default{
    transform: translateY(0);
    height: 22px;
    width: 38px;
    &.en {
      width: 81px;
    }
  }
}
</style>
