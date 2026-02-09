<template>
  <div class="sandbox-config-info-box">
    <!-- 折叠 info 功能 -->
    <div
      :class="['collapse-box', { collapse: !isCollapse }]"
      @click="isCollapse = !isCollapse"
    >
      <i class="paasng-icon paasng-angle-double-down"></i>
    </div>
    <!-- 配置信息 -->
    <template v-if="!isCollapse">
      <p class="alert mb-12 mt-10">
        <i class="paasng-icon paasng-info-line"></i>
        <span>{{ $t('沙箱环境复用 “预发布环境” 的增强服务和环境变量') }}</span>
      </p>
      <div class="info">
        <div class="info-item">
          <div class="label">{{ $t('代码仓库') }}：</div>
          <div
            class="value text-ellipsis"
            v-bk-overflow-tips="{ content: repoUrl, allowHTML: true }"
          >
            {{ repoUrl }}
          </div>
        </div>
        <div class="info-item">
          <div class="label">{{ $t('代码分支') }}：</div>
          <div class="value text-ellipsis">
            {{ repoBranch }}
            <a
              :href="repoBranchUrl"
              target="_blank"
            >
              <i class="paasng-jump-link paasng-icon"></i>
            </a>
          </div>
        </div>
        <div class="info-item">
          <div class="label">{{ $t('增强服务') }}：</div>
          <div
            class="value text-ellipsis"
            v-bk-overflow-tips
          >
            {{ displayServices }}
          </div>
        </div>
        <div class="info-item">
          <div class="label">{{ $t('环境变量') }}：</div>
          <div class="value">{{ $t('共 {n} 个', { n: this.sandboxEnvVars?.length ?? 0 }) }}</div>
        </div>
      </div>
    </template>
    <div class="flex-row align-center mt-16">
      <bk-input
        v-model="searchValue"
        :clearable="true"
        :placeholder="$t('请输入关键字搜索环境变量')"
        :right-icon="'bk-icon icon-search'"
        ext-cls="paas-custom-input-dark-cls"
      />
      <bk-button
        ext-cls="add-env-btn"
        theme="default"
        icon="plus"
        class="ml8"
        v-bk-tooltips="htmlConfig"
        @click="initEnvPopover(null, 'addEnvPopover')"
      />
      <EnvPopoverContent
        ref="addEnvPopover"
        id="sandbox-env-html"
        type="add"
        :title="$t('新增环境变量')"
        @confirm="handleAddEnv"
        @hide="hidePopover"
      />
    </div>
    <section
      v-bkloading="{ isLoading, color: 'rgba(255, 255, 255, 0.1)', zIndex: 10 }"
      class="env-variables-box mt-16"
    >
      <!-- 环境变量-空状态 -->
      <table-empty
        v-if="!displayEnvVars?.length"
        :keyword="searchValue ? 'placeholder' : ''"
        @clear-filter="searchValue = ''"
      />
      <ul v-else>
        <li
          v-for="(item, index) in displayEnvVars"
          :key="`${item.key}-${index}`"
          class="item"
        >
          <i
            class="paasng-icon paasng-user-8 mr8"
            :class="{ hidden: item.source !== 'custom' }"
            v-bk-tooltips="$t('自定义环境变量')"
          />
          <div class="content flex-row flex-column">
            <div class="key flex-1 text-ellipsis f12">{{ item.key }}</div>
            <div
              class="value flex-1 text-ellipsis f12"
              v-bk-overflow-tips
            >
              {{ item.is_sensitive ? "******" : item.value || '--' }}

            </div>
          </div>
          <div class="actions">
            <i
              class="paasng-icon paasng-edit-2"
              v-bk-tooltips="editHtmlConfig"
              @click="initEnvPopover(item, `editEnvPopover-${index}`)"
            />
            <EnvPopoverContent
              :ref="`editEnvPopover-${index}`"
              id="edit-sandbox-env-html"
              type="edit"
              :title="$t('编辑环境变量')"
              @confirm="handleAddEnv"
              @hide="hidePopover"
            />
            <i
              class="paasng-icon paasng-delete ml10"
              @click="showDeleteInfo(item.key, index)"
            />
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>

<script>
import EnvPopoverContent from './env-popover-content.vue';

export default {
  name: 'SandboxConfigInfo',
  components: {
    EnvPopoverContent,
  },
  inject: ['envData', 'getSandboxEnvVars'],
  props: {
    data: {
      type: Object,
      default: () => ({}),
    },
    serviceName: {
      type: String,
      default: '',
    },
    env: {
      type: String,
    },
  },
  data() {
    return {
      searchValue: '',
      tooltipInstances: new Map(), // 使用 Map 存储多个 tooltip 实例
      addonsServices: [],
      isCollapse: false,
    };
  },
  computed: {
    code() {
      return this.$route.query.code;
    },
    module() {
      return this.$route.query.module;
    },
    devSandboxCode() {
      return this.$route.query.devSandboxCode;
    },
    repoUrl() {
      return this.data?.repo?.url || '--';
    },
    repoBranch() {
      return this.data?.repo?.version_info?.version_name || '--';
    },
    repoBranchUrl() {
      if (this.repoUrl === '--' || this.repoBranch === '--') {
        return '--';
      }

      return `${this.repoUrl.replace(/\.git$/, '')}/tree/${encodeURIComponent(this.repoBranch)}`;
    },
    isLoading() {
      return this.envData.isEnvLoading;
    },
    // 沙箱环境变量
    sandboxEnvVars() {
      return this.envData.sandboxEnvVars;
    },
    displayEnvVars() {
      if (!this.searchValue) {
        return this.sandboxEnvVars;
      }
      const searchTerm = this.searchValue.toLowerCase();
      return this.sandboxEnvVars.filter(
        ({ key, value }) => key.toLowerCase().includes(searchTerm) || value.toLowerCase().includes(searchTerm)
      );
    },
    htmlConfig() {
      return this.baseHtmlConfig('#sandbox-env-html', 'add');
    },
    editHtmlConfig() {
      return this.baseHtmlConfig('#edit-sandbox-env-html', 'edit');
    },
    displayServices() {
      return this.addonsServices.map((service) => service.display_name)?.join('，');
    },
  },
  created() {
    this.getSandboxAddonsServices();
  },
  beforeDestroy() {
    // 组件销毁前清理所有 tooltip 实例
    this.tooltipInstances.forEach((instance) => {
      instance?.destroy();
    });
    this.tooltipInstances.clear();
  },
  methods: {
    baseHtmlConfig(contentSelector, instanceKey) {
      return {
        allowHTML: true,
        width: 400,
        trigger: 'click',
        theme: 'tomato',
        content: contentSelector,
        placement: 'bottom-end',
        extCls: 'sandbox-env-popover-cls',
        onMount: (instance) => {
          this.tooltipInstances.set(instanceKey, instance);
        },
      };
    },

    // 通过实例控制 tooltip
    hideTooltipByKey(key) {
      const instance = this.tooltipInstances.get(key);
      if (instance) {
        try {
          instance.hide();
        } catch (error) {
          console.warn(`Error hiding tooltip for key ${key}:`, error);
        }
      }
    },

    // 隐藏弹窗
    hidePopover() {
      this.tooltipInstances.forEach((instance, key) => {
        this.hideTooltipByKey(key);
      });
    },

    initEnvPopover(item, refName) {
      const ref = this.$refs[refName];
      const popover = Array.isArray(ref) ? ref[0] : ref;
      popover?.init?.(item);
    },

    async handleEnvAction(action, additionalPayload, successMessage) {
      try {
        const payload = {
          appCode: this.code,
          moduleId: this.module,
          devSandboxCode: this.devSandboxCode,
          ...additionalPayload,
        };
        await this.$store.dispatch(action, payload);
        this.$paasMessage({
          theme: 'success',
          message: successMessage,
        });
        this.getSandboxEnvVars();
        this.hidePopover();
      } catch (error) {
        this.catchErrorHandler(error);
      }
    },

    // 添加环境变量
    async handleAddEnv(formData, type = 'add') {
      const message = type === 'add' ? this.$t('添加成功') : this.$t('编辑成功');
      await this.handleEnvAction('sandbox/sandboxAddEnv', { data: formData }, message);
    },

    // 删除环境变量
    async handleDeleteEnv(envVarKey) {
      await this.handleEnvAction('sandbox/sandboxDelEnv', { envVarKey }, this.$t('删除成功'));
    },

    showDeleteInfo(envVarKey) {
      this.$bkInfo({
        title: this.$t('确认删除该环境变量？'),
        confirmFn: () => {
          this.handleDeleteEnv(envVarKey);
        },
      });
    },

    // 获取增强服务
    async getSandboxAddonsServices() {
      try {
        const res = await this.$store.dispatch('sandbox/getSandboxAddonsServices', {
          appCode: this.code,
          moduleId: this.module,
          devSandboxCode: this.devSandboxCode,
        });
        this.addonsServices = res;
      } catch (error) {
        this.catchErrorHandler(error);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.sandbox-config-info-box {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px;
  .collapse-box {
    position: absolute;
    left: 0;
    top: 0;
    width: 50%;
    height: 12px;
    line-height: 12px;
    text-align: center;
    cursor: pointer;
    background: #2e2e2e;
    border-radius: 0 0 2px 2px;
    i {
      font-size: 10px;
      color: #979ba5;
      transform: translateY(-2px);
    }
    &.collapse i {
      transform: rotate(180deg) translateY(3px);
    }
  }
  .alert {
    color: #979ba5;
    font-size: 12px;
    i {
      color: #979ba5;
      font-size: 14px;
      margin-right: 10px;
    }
  }
  .add-env-btn {
    width: 32px;
    color: #b3b3b3;
    padding: 0px !important;
    background-color: transparent;
  }
  .info {
    .info-item {
      display: flex;
      font-size: 12px;
      margin-bottom: 8px;
      .label {
        flex-shrink: 0;
        color: #979ba5;
      }
      .value {
        color: #dcdee5;
      }
      &:last-child {
        margin-bottom: 0;
      }
    }
  }
  .env-variables-box {
    flex: 1;
    overflow-y: auto;
    color: #63656e;
    &::-webkit-scrollbar {
      width: 4px;
      background-color: lighten(transparent, 80%);
    }
    &::-webkit-scrollbar-thumb {
      height: 5px;
      border-radius: 2px;
      background-color: #dcdee5;
    }
    .item {
      display: flex;
      align-items: center;
      height: 52px;
      background: #2e2e2e;
      padding: 0 10px;
      color: #c4c6cc;
      border-radius: 2px;
      margin-bottom: 8px;
      border: 1px solid #4d4f56;
      &:last-child {
        margin-bottom: 0;
      }
      i {
        color: #979ba5;
        transform: translateY(1px);
        &.hidden {
          visibility: hidden;
        }
      }
      .content {
        flex: 1;
        overflow: hidden;

        .key,
        .value {
          line-height: 20px;
        }
        .value {
          color: #979ba5;
        }
      }
      .actions {
        flex-shrink: 0;
        i:hover {
          cursor: pointer;
          color: #3a84ff;
        }
        i.paasng-delete:hover {
          color: #ea3636;
        }
      }
    }
  }
}
</style>

<style lang="scss">
.sandbox-env-popover-cls {
  .tippy-tooltip.tomato-theme,
  .tippy-tooltip.del-tomato-theme {
    padding: 0 !important;
    background-color: #2e2e2e !important;
    color: #979ba5 !important;
    box-shadow: 2px 2px 4px 0 #0000001a, -2px 2px 4px 0 #0000001a, 0 2px 6px 0 #00000021;
  }
  .add-env-popover-content {
    padding-top: 16px;
    .popover-title {
      padding: 0 16px;
      font-size: 16px;
      color: #e6e6e6;
    }
    .popover-body {
      padding: 16px;
    }
    .popover-footer {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      padding: 0 16px;
      height: 48px;
      background: #3d3d3d;
      border-radius: 0 0 2px 2px;
    }
  }
}
</style>
