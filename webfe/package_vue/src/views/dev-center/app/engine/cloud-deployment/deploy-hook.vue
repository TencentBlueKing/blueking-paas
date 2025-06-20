<template>
  <div :class="['deploy-hook-container', { special: !isCreate }]">
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="deploy-hook-loading"
      :offset-top="0"
      :offset-left="0"
      :local-loading="false"
      :is-transition="false"
      class="deploy-action-box"
    >
      <div class="form-pre">
        <div
          class="flex-row align-items-center pl20 pr20"
          v-if="!isCreate"
        >
          <div class="item-title-container">
            <div class="item-title">
              {{ $t('部署前置命令') }}
            </div>
          </div>
          <div
            class="edit-container"
            @click="handleEditClick"
            v-if="!isPageEdit && !isReadOnlyMode"
          >
            <i class="paasng-icon paasng-edit-2" />
            {{ $t('编辑') }}
          </div>
        </div>
        <div class="deploy-command-tip">
          {{ $t('部署前置命令在独立容器中执行，适用于数据库表变更等操作。') }}
          <a
            :href="GLOBAL.DOC.DEPLOY_ORDER"
            target="_blank"
          >
            {{ $t('使用指南') }}
          </a>
        </div>
        <!-- 不启用时隐藏 -->
        <bk-form
          v-if="isPageEdit"
          ref="commandRef"
          :model="preFormData"
          class="info-special-form form-pre-command"
        >
          <bk-form-item
            :label="$t('是否启用')"
            class="pt20"
          >
            <bk-switcher
              v-if="isPageEdit"
              v-model="preFormData.enabled"
              theme="primary"
              @change="switcherChange"
            />
          </bk-form-item>
          <bk-form-item
            v-if="preFormData.enabled"
            :label="$t('启动命令')"
            :required="true"
            :rules="rules.command"
            :error-display-type="'normal'"
          >
            <bk-tag-input
              v-model="preFormData.command"
              style="width: 500px"
              placeholder=" "
              :allow-create="allowCreate"
              :allow-auto-match="true"
              :has-delete-icon="hasDeleteIcon"
              :paste-fn="copyCommand"
            />
            <span
              slot="tip"
              class="whole-item-tips"
            >
              {{ $t("数组类型，示例数据：['/process_data']，按回车键分隔每个元素") }}
              <br />
              {{ $t('在每次部署前执行。如需执行多条命令请将其封装在一个脚本中，如：') }}
              ['/bin/sh', './bin/pre-task.sh']
            </span>
          </bk-form-item>
          <bk-form-item
            v-if="preFormData.enabled"
            :label="$t('命令参数')"
            class="pt20 hook-form-cls"
          >
            <bk-tag-input
              v-model="preFormData.args"
              style="width: 500px"
              ext-cls="tag-extra"
              placeholder=" "
              :allow-create="allowCreate"
              :allow-auto-match="true"
              :has-delete-icon="hasDeleteIcon"
              :paste-fn="copyCommandParameter"
            />
            <span class="whole-item-tips">
              {{ $t("数组类型，示例数据：['--dataset', 'myset']，按回车键分隔每个元素") }}
            </span>
          </bk-form-item>
        </bk-form>
        <bk-form
          v-if="!isPageEdit"
          :model="preFormData"
          class="info-special-form form-pre-command"
        >
          <bk-form-item
            :label="`${$t('是否启用')}：`"
            class="pt20"
          >
            <span :class="['hook-tag', { enabled: preFormData.enabled }]">
              {{ preFormData.enabled ? $t('已启用') : $t('未启用') }}
            </span>
          </bk-form-item>
          <!-- 非镜像模块查看态-展示 proc_command -->
          <bk-form-item
            :label="`${$t('启动命令')}：`"
            v-if="preFormData.enabled && isReadOnlyMode && readonlyStartupCommand"
          >
            {{ readonlyStartupCommand }}
          </bk-form-item>
          <template v-else>
            <bk-form-item
              v-if="preFormData.enabled"
              :label="`${$t('启动命令')}：`"
            >
              <div
                class="hook-tag-cls"
                v-if="preFormData.command.length"
              >
                <bk-tag
                  v-for="item in preFormData.command"
                  :key="item"
                >
                  {{ item }}
                </bk-tag>
              </div>
              <div v-else>--</div>
            </bk-form-item>
            <bk-form-item
              v-if="preFormData.enabled"
              :label="`${$t('命令参数')}：`"
              class="pt20 hook-form-cls"
            >
              <div
                class="hook-tag-cls"
                v-if="preFormData.args.length"
              >
                <bk-tag
                  v-for="item in preFormData.args"
                  :key="item"
                >
                  {{ item }}
                </bk-tag>
              </div>
              <div v-else>--</div>
            </bk-form-item>
          </template>
        </bk-form>
        <!-- 创建应用/模块不展示 -->
        <div
          class="hook-btn-wrapper"
          v-if="isPageEdit && !isCreate"
        >
          <bk-button
            :loading="saveLoading"
            :theme="'primary'"
            @click="handleSave"
          >
            {{ $t('保存') }}
          </bk-button>
          <bk-button
            class="ml8"
            @click="handleCancel"
          >
            {{ $t('取消') }}
          </bk-button>
        </div>
      </div>
    </paas-content-loader>
  </div>
</template>

<script>
import { cloneDeep } from 'lodash';
import i18n from '@/language/i18n.js';

export default {
  props: {
    moduleId: {
      type: String,
      default: '',
    },
    isCreate: {
      type: Boolean,
      default: false,
    },
    saveLoading: {
      type: Boolean,
      default: false,
    },
    // 组件内部按钮操作
    isComponentBtn: {
      type: Boolean,
      default: false,
    },
  },

  data() {
    return {
      isPageEdit: false,
      panels: [],
      preFormData: {
        enabled: false,
        command: [],
        args: [],
      },
      allowCreate: true,
      hasDeleteIcon: true,
      isLoading: false,
      hooks: null,
      cloudInfoTip: i18n.t('web进程的容器镜像地址'),
      rawData: {},
      rules: {
        command: [
          {
            validator: () => {
              if (this.preFormData.command.length) {
                return true;
              }
              return false;
            },
            message: () => `${this.$t('必填项')}`,
            trigger: 'blur',
          },
        ],
      },
    };
  },

  computed: {
    curAppModule() {
      return this.$store.state.curAppModule;
    },
    isCustomImage() {
      return this.curAppModule?.web_config?.runtime_type === 'custom_image';
    },
    appCode() {
      return this.$route.params.id;
    },
    curModuleId() {
      return this.curAppModule?.name;
    },
    // 非镜像模块、创建模块、应用为查看模式
    isReadOnlyMode() {
      return !this.isCustomImage && !this.isCreate;
    },
    // 只读模式展示的启动命令
    readonlyStartupCommand() {
      return this.preFormData?.proc_command;
    },
  },

  created() {
    // 非创建应用初始化为查看态
    if (!this.isCreate) {
      this.$store.commit('cloudApi/updatePageEdit', false);
      this.$store.commit('cloudApi/updateHookPageEdit', false);
      this.init();
    }
  },

  methods: {
    // 获取hooks信息
    async init() {
      try {
        this.isLoading = true;
        const res = await this.$store.dispatch('deploy/getAppReleaseHook', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.preFormData = { ...res };
        this.rawData = cloneDeep(res);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message,
        });
      } finally {
        this.isLoading = false;
      }
    },
    switcherChange(value) {
      this.$set(this.preFormData, 'enabled', value);
      if (!this.preFormData.enabled) {
        this.preFormData.command = [];
        this.preFormData.args = [];
      }
    },

    trimStr(str) {
      return str.replace(/(^\s*)|(\s*$)/g, '');
    },

    copyCommand(val) {
      const value = this.trimStr(val);
      if (!value) {
        this.$bkMessage({ theme: 'error', message: this.$t('粘贴内容不能为空'), delay: 2000, dismissable: false });
        return [];
      }
      const commandArr = value.split(',');
      commandArr.forEach((item) => {
        if (!this.preFormData.command.includes(item)) {
          this.preFormData.command.push(item);
        }
      });
      return this.preFormData.command;
    },

    copyCommandParameter(val) {
      const value = this.trimStr(val);
      if (!value) {
        this.$bkMessage({ theme: 'error', message: this.$t('粘贴内容不能为空'), delay: 2000, dismissable: false });
        return [];
      }
      const commandArr = value.split(',');
      commandArr.forEach((item) => {
        if (!this.preFormData.args.includes(item)) {
          this.preFormData.args.push(item);
        }
      });
      return this.preFormData.args;
    },

    // tab不在当前项进行发布，校验调用防止警告
    formDataValidate(index) {
      if (index) {
        return false;
      }
    },

    // 编辑
    handleEditClick() {
      // 使用页面编辑
      this.isPageEdit = true;
    },

    // 校验
    async handleValidator() {
      let flag = true;
      try {
        if (this.$refs.commandRef) {
          await this.$refs.commandRef.validate();
        }
      } catch (e) {
        flag = false;
      }
      return flag;
    },

    // 保存
    async handleSave() {
      if (this.$refs.commandRef) {
        try {
          await this.$refs.commandRef.validate();
        } catch (error) {
          return false;
        }
      }
      // 如果是创建
      if (this.isCreate) {
        return { ...this.preFormData };
      }
      try {
        await this.$store.dispatch('deploy/saveAppReleaseHook', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          params: { ...this.preFormData },
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('保存成功！'),
        });
        this.isPageEdit = false;
        this.init();
      } catch (error) {
        this.$paasMessage({
          theme: 'error',
          message: error.detail || error.message,
        });
      }
    },

    // 数据还原
    handleCancel() {
      this.isPageEdit = false;
      this.preFormData = cloneDeep(this.rawData);
    },
  },
};
</script>

<style lang="scss" scoped>
.form-pre {
  padding-bottom: 20px;
  /deep/ .bk-form-item {
    position: relative;
  }

  .item-title-container {
    display: flex;
    align-items: center;
  }

  .item-title {
    font-size: 14px;
    font-weight: bold;
    color: #313238;
  }

  .item-info {
    font-size: 14px;
    color: #313238;
    margin: 24px 0 0 30px;
  }

  .whole-item-tips {
    line-height: 26px;
    color: #979ba5;
    font-size: 12px;
  }

  .hook-btn-wrapper {
    margin-left: 150px;
    margin-top: 24px;
  }

  .deploy-command-tip {
    padding-left: 20px;
    color: #979ba5;
    font-size: 12px;
    margin-top: 8px;
  }
}

.info-special-form.bk-form.bk-inline-form {
  width: auto;
}

.form-pre-command.bk-form.bk-inline-form .bk-form-input {
  height: 32px !important;
}

.hook-form-cls {
  margin-top: 0;
}
.value-cls {
  color: #313238;
}
.edit-container {
  color: #3a84ff;
  font-size: 12px;
  cursor: pointer;
  padding-left: 12px;
  i {
    padding-left: 10px;
  }
}
.hook-tag {
  display: inline-block;
  height: 22px;
  padding: 0 8px;
  font-size: 12px;
  line-height: 22px;
  color: #63656e;
  background: #f0f1f5;
  border-radius: 2px;
  &.enabled {
    color: #14a568;
    background: #e4faf0;
  }
}
.deploy-hook-container.special {
  min-height: 200px;
}
.hook-tag-cls .bk-tag:first-child {
  margin-left: 0px;
}
</style>
