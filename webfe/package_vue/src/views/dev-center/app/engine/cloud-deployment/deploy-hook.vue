<template>
  <paas-content-loader
    :is-loading="isLoading"
    placeholder="deploy-hook-loading"
    :offset-top="0"
    :offset-left="0"
    :is-transition="false"
    class="deploy-action-box"
  >
    <div class="form-pre">
      <div class="flex-row align-items-center">
        <div class="item-title-container">
          <div class="item-title">
            {{ $t('部署前置命令') }}
          </div>
          <bk-switcher
            v-if="isPageEdit"
            class="ml20 mr10"
            v-model="preFormData.loaclEnabled"
            theme="primary"
            @change="switcherChange"
          />
          <div
            v-else
            class="ml10"
          >
            <bk-tag
              :key="preFormData.loaclEnabled ? $t('已启用') : $t('未启用')"
              :theme="preFormData.loaclEnabled ? 'info' : ''"
            >
              {{ preFormData.loaclEnabled ? $t('已启用') : $t('未启用') }}
            </bk-tag>
          </div>
        </div>
        <!-- <bk-button
          v-if="!isPageEdit"
          class="fr"
          theme="primary"
          title="编辑"
          :outline="true"
          @click="handleEditClick">
          {{ $t('编辑') }}
        </bk-button> -->

        <div
          class="edit-container"
          @click="handleEditClick"
          v-if="!isPageEdit"
        >
          <i class="paasng-icon paasng-edit-2 pl10" />
          {{ $t('编辑') }}
        </div>
      </div>
      <!-- 不启用时隐藏 -->
      <bk-form
        v-if="isPageEdit && preFormData.loaclEnabled"
        ref="commandRef"
        :model="preFormData"
        :label-width="100"
        class="info-special-form form-pre-command"
      >
        <bk-form-item
          :label="$t('启动命令')"
          :required="true"
          :rules="rules.command"
          :error-display-type="'normal'"
          class="pt20"
          style="position: relative; margin-left: 5px"
        >
          <bk-tag-input
            v-model="preFormData.command"
            style="width: 500px"
            :placeholder="$t('请输入启动命令')"
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
          :label="$t('命令参数')"
          class="pt20 hook-form-cls"
          style="width: 510px; position: relative; margin-left: 5px"
        >
          <bk-tag-input
            v-model="preFormData.args"
            style="width: 500px"
            ext-cls="tag-extra"
            :placeholder="$t('请输入命令参数')"
            :allow-create="allowCreate"
            :allow-auto-match="true"
            :has-delete-icon="hasDeleteIcon"
            :paste-fn="copyCommandParameter"
          />
          <span class="whole-item-tips">{{ $t('示例：--env prod，多个参数可用回车键分隔') }}</span>
        </bk-form-item>
      </bk-form>
      <bk-form
        v-if="!isPageEdit && preFormData.loaclEnabled"
        :model="preFormData"
        :label-width="100"
        class="info-special-form form-pre-command"
      >
        <bk-form-item
          :label="$t('启动命令')"
          class="pt20"
          style="position: relative; margin-left: 5px"
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
          :label="$t('命令参数')"
          class="pt20 hook-form-cls"
          style="position: relative; margin-left: 5px"
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
          @click="$emit('cancel')"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </div>
  </paas-content-loader>
</template>

<script>
import _ from 'lodash';
import i18n from '@/language/i18n.js';

export default {
  props: {
    moduleId: {
      type: String,
      default: '',
    },
    cloudAppData: {
      type: Object,
      default: {},
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
        loaclEnabled: false,
        command: [],
        args: [],
      },
      allowCreate: true,
      hasDeleteIcon: true,
      isLoading: true,
      localCloudAppData: {},
      hooks: null,
      processData: [],
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
  },

  watch: {
    cloudAppData: {
      handler(val) {
        if (val.spec) {
          this.localCloudAppData = _.cloneDeep(val);
          this.processData = val.spec.processes;
          this.hooks = val.spec.hooks;
          this.preFormData.loaclEnabled = !!this.hooks;
          if (this.preFormData.loaclEnabled) {
            this.preFormData.command = (this.hooks && this.hooks.preRelease.command) || [];
            this.preFormData.args = (this.hooks && this.hooks.preRelease.args) || [];
          }
          this.formData = this.processData[this.panelActive];
          this.rawData = _.cloneDeep(this.preFormData);
        }
        setTimeout(() => {
          this.isLoading = false;
        }, 500);
      },
      immediate: true,
      // deep: true
    },
    preFormData: {
      handler(val) {
        if (this.localCloudAppData.spec) {
          let hooks = { preRelease: { command: val.command, args: val.args } };
          if (!this.preFormData.loaclEnabled) {
            hooks = null;
          }
          this.$set(this.localCloudAppData.spec, 'hooks', hooks);
          this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
        }
      },
      immediate: true,
      deep: true,
    },
  },

  created() {
    // 非创建应用初始化为查看态
    if (!this.isCreate) {
      this.$store.commit('cloudApi/updatePageEdit', false);
      this.$store.commit('cloudApi/updateHookPageEdit', false);
    }
  },

  methods: {
    switcherChange(value) {
      this.$set(this.preFormData, 'loaclEnabled', value);
      if (!this.preFormData.loaclEnabled) {
        this.$set(this.localCloudAppData.spec, 'hooks', null);
      } else {
        this.$set(this.localCloudAppData.spec, 'hooks', { preRelease: { command: this.preRelease?.command || [], args: this.preRelease?.args || [] } });
      }
      this.$store.commit('cloudApi/updateCloudAppData', this.localCloudAppData);
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
    handleSave() {
      if (this.$refs.commandRef) {
        this.$refs.commandRef.validate().then(
          () => {
            this.$emit('save');
            this.$nextTick(() => {
              this.rawData = _.cloneDeep(this.preFormData);
            });
          },
          (err) => {
            console.error(err);
          },
        );
      } else {
        this.$emit('save');
      }
    },

    // 数据还原
    handleCancel() {
      this.$refs.commandRef.clearError();
      this.preFormData.command = this.rawData.command;
      this.preFormData.args = this.rawData.args;
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
}
</style>
