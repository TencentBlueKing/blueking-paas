<template>
  <paas-content-loader
    :is-loading="isLoading"
    placeholder="deploy-hook-loading"
    :offset-top="0"
    :offset-left="0"
    :is-transition="false"
    class="deploy-action-box"
  >
    <!-- 若托管方式为源码&镜像，钩子命令页面都为当前空页面状态 -->
    <section
      v-if="!isCustomImage && !isCreate"
      style="margin-top: 38px;"
    >
      <bk-exception
        class="exception-wrap-item exception-part"
        type="empty"
        scene="part"
      >
        <p
          class="mt10"
          style="color: #979BA5;font-size: 12px;"
        >
          {{ $t('钩子命令在构建目录下的 app_desc.yaml 文件中定义。') }}
        </p>
        <p class="guide-link mt15" @click="handleViewGuide">{{ $t('查看使用指南') }}</p>
      </bk-exception>
    </section>
    <div
      v-else
      class="form-pre"
    >
      <div class="flex-row align-items-center">
        <div class="item-title-container">
          <div class="item-title">
            {{ $t('部署前置命令') }}
          </div>
        </div>

        <div
          class="edit-container"
          @click="handleEditClick"
          v-if="!isPageEdit"
        >
          <i class="paasng-icon paasng-edit-2" />
          {{ $t('编辑') }}
        </div>
      </div>
      <!-- 不启用时隐藏 -->
      <bk-form
        v-if="isPageEdit"
        ref="commandRef"
        :model="preFormData"
        :label-width="158"
        class="info-special-form form-pre-command"
      >
        <bk-form-item
          :label="$t('是否启用')"
          class="pt20"
          style="position: relative;"
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
          style="position: relative;"
        >
          <bk-tag-input
            v-model="preFormData.command"
            style="width: 500px"
            :placeholder="$t('请输入启动命令，并按 Enter 键结束')"
            :allow-create="allowCreate"
            :allow-auto-match="true"
            :has-delete-icon="hasDeleteIcon"
            :paste-fn="copyCommand"
          />
          <span
            slot="tip"
            class="whole-item-tips"
          >
            {{ $t('在每次部署前执行。如需执行多条命令请将其封装在一个脚本中，如：') }}./bin/pre-task.sh
          </span>
        </bk-form-item>
        <bk-form-item
          v-if="preFormData.enabled"
          :label="$t('命令参数')"
          class="pt20 hook-form-cls"
          style="position: relative;"
        >
          <bk-tag-input
            v-model="preFormData.args"
            style="width: 500px"
            ext-cls="tag-extra"
            :placeholder="$t('请输入命令参数，并按 Enter 键结束')"
            :allow-create="allowCreate"
            :allow-auto-match="true"
            :has-delete-icon="hasDeleteIcon"
            :paste-fn="copyCommandParameter"
          />
          <span class="whole-item-tips">{{ $t('示例：--env prod，多个参数可用回车键分隔') }}</span>
        </bk-form-item>
      </bk-form>
      <bk-form
        v-if="!isPageEdit"
        :model="preFormData"
        :label-width="158"
        class="info-special-form form-pre-command pl40"
      >
        <bk-form-item
          :label="`${$t('是否启用')}：`"
          class="pt20"
          style="position: relative;"
        >
          <bk-tag
            :key="preFormData.enabled ? $t('已启用') : $t('未启用')"
            :theme="preFormData.enabled ? 'info' : ''"
          >
            {{ preFormData.enabled ? $t('已启用') : $t('未启用') }}
          </bk-tag>
        </bk-form-item>
        <bk-form-item
          v-if="preFormData.enabled"
          :label="`${$t('启动命令')}：`"
          style="position: relative;"
        >
          <div v-if="preFormData.command.length">
            <bk-tag
              v-for="item in preFormData.command"
              :key="item"
            >
              {{ item }}
            </bk-tag>
          </div>
          <div
            v-else
            class="pl10"
          >
            --
          </div>
        </bk-form-item>
        <bk-form-item
          v-if="preFormData.enabled"
          :label="`${$t('命令参数')}：`"
          class="pt20 hook-form-cls"
          style="position: relative;"
        >
          <div v-if="preFormData.args.length">
            <bk-tag
              v-for="item in preFormData.args"
              :key="item"
            >
              {{ item }}
            </bk-tag>
          </div>
          <div
            v-else
            class="pl10"
          >
            --
          </div>
        </bk-form-item>
      </bk-form>
      <div
        class="hook-btn-wrapper"
        v-if="isPageEdit && isComponentBtn"
      >
        <bk-button
          :loading="saveLoading"
          class="pl20 pr20"
          :theme="'primary'"
          @click="handleSave"
        >
          {{ $t('保存') }}
        </bk-button>
        <bk-button
          class="pl20 pr20 ml20"
          @click="handleCancel"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </div>

    <user-guide name="hook" ref="userGuideRef" />
  </paas-content-loader>
</template>

<script>import _ from 'lodash';
import i18n from '@/language/i18n.js';
import userGuide from './comps/user-guide/index.vue';

export default {
  components: {
    userGuide,
  },
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
    isPageEdit() {
      return this.$store.state.cloudApi.isPageEdit || this.$store.state.cloudApi.hookPageEdit;
    },
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
        this.rawData = _.cloneDeep(this.preFormData);
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
      if (this.isCreate) {
        this.$store.commit('cloudApi/updateHookPageEdit', true);
      } else {
        this.$store.commit('cloudApi/updatePageEdit', true);
      }
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
        this.$store.commit('cloudApi/updateHookPageEdit', false);
        this.$store.commit('cloudApi/updatePageEdit', false);
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
      this.init();
      this.$store.commit('cloudApi/updatePageEdit', false);
      this.$store.commit('cloudApi/updateHookPageEdit', false);
    },

    // 查看指南
    handleViewGuide() {
      this.$refs.userGuideRef.showSideslider();
    },
  },
};
</script>

<style lang="scss" scoped>
.form-pre {
  padding: 0 20px 20px;

  .item-title-container {
    display: flex;
    align-items: center;
  }

  .item-title {
    font-size: 14px;
    font-weight: bold;
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
    margin-left: 105px;
    margin-top: 24px;
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
  padding-left: 10px;
  i {
    padding-left: 10px;
  }
}
</style>
