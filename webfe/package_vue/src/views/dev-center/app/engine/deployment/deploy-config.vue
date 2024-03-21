<template>
  <paas-content-loader
    :is-loading="isLoading"
    placeholder="deploy-config-loading"
    :offset-top="0"
    :offset-left="-8"
    class="config-warp"
  >
    <bk-form
      class="info-special-form"
      form-type="inline"
    >
      <bk-form-item style="width: 165px;">
        <label class="title-label"> {{ $t('部署前置命令') }} </label>
        <i
          v-bk-tooltips="configDirTip"
          class="paasng-icon paasng-info-circle tooltip-icon"
        />
      </bk-form-item>
      <div class="pt5">
        <div
          :class="['ps-switcher-wrapper', 'start-command-cls', { disabled: isPreDeployCommandDisabled }]"
          @click="togglePermission"
        >
          <bk-switcher
            :disabled="isPreDeployCommandDisabled"
            v-model="configInfo.loaclEnabled"
          />
        </div>
        <span class="pl5">{{ configInfo.loaclEnabled ? $t('已启用') : $t('未启用') }}</span>
      </div>
      <bk-form-item
        class="pt20"
        style="width: calc(100% - 260px); position:relative"
      >
        <bk-input
          v-if="configInfo.loaclEnabled"
          ref="nameInput"
          v-model="configInfo.command"
          :placeholder="$t('请输入')"
          :readonly="!isEdited"
          ext-cls="paas-info-app-name-cls"
          :clearable="false"
        />
        <!-- <bk-button
                    class="config-button"
                    theme="primary"
                    :disabled="isEdited"
                    text
                    @click.stop.prevent="handlerCommand">
                    {{configInfo.enabled ? '确认禁用' : '确认启用'}}
                </bk-button> -->
        <span class="info">
          {{ $t('复杂命令可封装在一个脚本中，放在代码仓库的 bin 目录下(bin/pre-task.sh)，并将部署前置命令配置为:') }}
          "bash ./bin/pre-task.sh"</span>

        <div class="action-box">
          <template v-if="!isEdited">
            <a
              v-if="configInfo.loaclEnabled"
              v-bk-tooltips="$t('编辑')"
              class="paasng-icon paasng-edit2"
              @click="showEdit"
            />
          </template>
          <template v-else>
            <bk-button
              v-if="configInfo.loaclEnabled"
              style="margin-right: 6px;"
              theme="primary"
              :disabled="configInfo.command === ''"
              text
              @click.stop.prevent="saveCommand"
            >
              {{ $t('确认启用-button') }}
            </bk-button>
            <bk-button
              v-if="configInfo.loaclEnabled"
              theme="primary"
              text
              @click.stop.prevent="cancelCommand"
            >
              {{ $t('取消') }}
            </bk-button>
          </template>
        </div>
      </bk-form-item>
    </bk-form>
    <bk-form
      v-if="curAppModule.web_config.runtime_type !== 'custom_image'"
      class="info-special-form pt20"
      form-type="inline"
    >
      <bk-form-item style="width: 165px;">
        <label class="title-label"> {{ $t('部署命令') }} </label>
      </bk-form-item>
      <bk-form-item>
        <p class="command">
          {{ $t('由应用代码根目录下的Procfile文件定义') }} <a
            :href="GLOBAL.DOC.PROCFILE_DOC"
            target="_blank"
            class="blue ml10"
          > {{ $t('文档：应用进程与Procfile') }} </a>
        </p>
      </bk-form-item>
    </bk-form>
    <bk-form
      v-if="isDockerApp"
      class="info-special-form pt20"
      form-type="inline"
      style="display: flex"
    >
      <bk-form-item style="width: 165px;margin-top: 18px;">
        <label class="title-label"> {{ $t('启动命令') }} </label>
      </bk-form-item>

      <bk-form-item v-if="curAppModule.web_config.runtime_type !== 'custom_image'">
        <p class="command">
          {{ $t('由应用代码根目录下的Procfile文件定义') }} <a
            :href="GLOBAL.DOC.PROCFILE_DOC"
            target="_blank"
            class="blue ml10"
          > {{ $t('文档：应用进程与Procfile') }} </a>
        </p>
      </bk-form-item>
      <bk-form-item
        v-else
        style="flex: 1"
      >
        <table
          class="ps-table ps-table-default ps-table-width-overflowed"
          style="margin-bottom: 24px;width: 100%"
        >
          <tr
            v-for="(varItem, index) in commandList"
            :key="index"
          >
            <td>
              <bk-form
                form-type="inline"
                :model="varItem"
                :rules="varRules"
                class="orderList"
                style="display: flex"
              >
                <bk-form-item
                  :property="'name'"
                  style="flex: 1 1 20%;padding-right: 10px"
                >
                  <bk-input
                    :ref="'varItem' + index"
                    v-model="varItem.name"
                    :clearable="false"
                    :readonly="isReadOnlyRow(index)"
                  />
                </bk-form-item>
                <bk-form-item
                  :property="'command'"
                  style="flex: 1 1 60%;"
                >
                  <bk-input
                    v-model="varItem.command"
                    :clearable="false"
                    :readonly="isReadOnlyRow(index)"
                  />
                </bk-form-item>
                <bk-form-item style="flex: 1 1 7%; text-align: right; min-width: 80px;">
                  <template v-if="isReadOnlyRow(index)">
                    <a
                      class="paasng-icon paasng-edit ps-btn ps-btn-icon-only btn-ms-primary"
                      @click="editingRowToggle(index)"
                    />
                    <tooltip-confirm
                      ref="deleteTooltip"
                      :ok-text="$t('确定')"
                      :cancel-text="$t('取消')"
                      :theme="'ps-tooltip'"
                      @ok="deleteConfigVar(varItem.name)"
                    >
                      <a
                        v-show="isReadOnlyRow(index)"
                        slot="trigger"
                        class="paasng-icon paasng-delete ps-btn ps-btn-icon-only btn-ms-primary"
                      />
                    </tooltip-confirm>
                  </template>
                  <template v-else>
                    <a
                      class="paasng-icon paasng-check-1 ps-btn ps-btn-icon-only"
                      type="submit"
                      @click="updateConfigVar(index)"
                    />
                    <a
                      class="paasng-icon paasng-close ps-btn ps-btn-icon-only"
                      style="margin-left: 0;"
                      @click="editingRowToggle(index)"
                    />
                  </template>
                </bk-form-item>
              </bk-form>
            </td>
          </tr>
          <tr v-if="curAppModule.web_config.runtime_type === 'custom_image'">
            <td>
              <bk-form
                ref="validate2"
                form-type="inline"
                :rules="varRules"
                :model="newVarConfig"
                style="display: flex"
              >
                <bk-form-item
                  :property="'name'"
                  style="flex: 1 1 20%;padding-right: 10px"
                >
                  <bk-input
                    ref="serverInput"
                    v-model="newVarConfig.name"
                    :placeholder="$t('名称，例如：web')"
                    :clearable="false"
                  />
                </bk-form-item>
                <bk-form-item
                  :property="'command'"
                  style="flex: 1 1 60%;"
                >
                  <bk-input
                    v-model="newVarConfig.command"
                    :placeholder="$t('启动命令。包含参数，例如：gunicorn wsgi -w 4 -b :$PORT')"
                    :clearable="false"
                  />
                </bk-form-item>
                <bk-form-item style="flex: 1 1 7%; text-align: right; min-width: 80px; margin-top: 5px;">
                  <bk-button
                    theme="primary"
                    :outline="true"
                    @click.stop.prevent="createConfigVar"
                  >
                    {{ $t('添加') }}
                  </bk-button>
                </bk-form-item>
              </bk-form>
            </td>
          </tr>
          <tr>
            <td>
              <bk-form-item>
                <p class="mt-minus">
                  {{ $t('在') }}<span @click="skip"> {{ $t('访问入口-进程服务管理') }} </span> {{ $t('中可设置将应用进程暴露给应用内部与外部用户') }}
                </p>
              </bk-form-item>
            </td>
          </tr>
        </table>
      </bk-form-item>
    </bk-form>
  </paas-content-loader>
</template>
<script>import _ from 'lodash';
import appBaseMixin from '@/mixins/app-base-mixin';
import tooltipConfirm from '@/components/ui/TooltipConfirm';
export default {
  components: {
    tooltipConfirm,
  },
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: false,
      isEdited: false,
      configInfo: { enabled: false, command: '', type: '', loaclEnabled: '' },
      configDirTip: {
        theme: 'light',
        allowHtml: true,
        content: this.$t('提示信息'),
        html: `<a target="_blank" href="${this.GLOBAL.DOC.DEPLOY_ORDER}" style="color: #3a84ff">${this.$t('部署前置命令')}</a>`,
        placements: ['right'],
      },
      editRowList: [],
      newVarConfig: {
        name: '',
        command: '',
      },
      varRules: {
        name: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
          {
            regex: /^[a-zA-Z0-9]([-a-zA-Z0-9]){0,11}$/,
            message: this.$t('只能包含字母、数字、连接符(-)'),
            trigger: 'blur',
          },
        ],
        command: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
          {
            regex: /^(?!start).*/,
            message: this.$t('不能以 start 开头'),
            trigger: 'blur',
          },
        ],
      },
      commandList: [],
      editIcon: true,
    };
  },
  computed: {
    curAppModule() {
      return this.$store.state.curAppModule;
    },
    isDockerApp() {
      return this.curAppModule.source_origin === 4;
    },
    curApplicationData() {
      return this.curAppInfo.application;
    },
    isDefaultApp() {
      return this.curApplicationData.type === 'default';
    },
    isDefaultAppFeature() {
      return this.isDefaultApp && !this.isSmartApp && !this.isDockerApp;
    },
    isPreDeployCommandDisabled() {
      if (!this.isDefaultApp) return true;
      // S-mart 应用：只展示查看态
      if (this.isDefaultApp && this.curApplicationData?.is_smart_app) return true;
      // 普通应用 ：只能停用
      if (this.isDefaultAppFeature && !this.configInfo.loaclEnabled) return true;
      return false;
    },
  },
  watch: {
    '$route'(newVal, oldVal) {
      console.log(newVal, oldVal);
      this.isLoading = true;
      this.init();
    },
  },
  mounted() {
    this.isLoading = true;
    this.init();
    this.inputFocusFun();
    console.log('curAppType', this.curApplicationData);
    console.log('this.curAppModule', this.curAppModule);
    // 查看态
    // isDefaultApp && isSmartApp

    // 普通应用-镜像应用
    // isDefaultApp && isDockerApp

    // 普通应用
    // isDefaultApp && !isSmartApp && !isDockerApp
  },
  methods: {
    async init() {
      try {
        const res = await this.$store.dispatch('deploy/getDeployConfig', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.commandList = res.procfile;
        this.configInfo.command = res.hooks.length ? res.hooks[0].command : '';
        this.configInfo.type = res.hooks.length ? res.hooks[0].type : 'pre-release-hook';
        this.configInfo.enabled = res.hooks.length ? res.hooks[0].enabled : false;
        this.configInfo.loaclEnabled = this.configInfo.enabled;
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isLoading = false;
      }
    },
    handlerCommand() {
      if (this.configInfo.enabled) {
        this.$bkInfo({
          title: this.$t('确认禁用?'),
          maskClose: true,
          confirmFn: () => {
            this.closeCommand();
          },
        });
      } else {
        this.$bkInfo({
          title: this.$t('确认启用?'),
          maskClose: true,
          confirmFn: () => {
            this.submitCommand();
          },
        });
      }
    },
    showEdit() {
      this.isEdited = true;
      this.localeConfigCommandTemp = this.configInfo.command;
      this.$refs.nameInput.focus();
    },
    saveCommand() {
      this.isEdited = false;
      // this.submitCommand()
      this.$bkInfo({
        width: 500,
        title: `${this.$t('确认启用模块')}${this.curAppModule.name}${this.$t('部署前置命令?')}`,
        subTitle: this.$t('启用后，部署预发布环境、生产环境时都将执行该命令'),
        maskClose: true,
        confirmFn: () => {
          this.submitCommand();
        },
      });
    },
    cancelCommand() {
      this.isEdited = false;
      this.configInfo.command = this.localeConfigCommandTemp;
      this.init();
    },
    async submitCommand() {
      const params = {
        type: this.configInfo.type,
        command: this.configInfo.command,
      };
      try {
        const res = await this.$store.dispatch('deploy/updateDeployConfig', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          params,
        });
        console.log('res', res);
        this.$paasMessage({
          limit: 1,
          theme: 'success',
          message: this.$t('已启用'),
        });
        this.init();
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    async closeCommand() {
      try {
        const res = await this.$store.dispatch('deploy/closeDeployConfig', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          type: this.configInfo.type,
        });
        console.log('res', res);
        this.$paasMessage({
          limit: 1,
          theme: 'success',
          message: this.$t('已禁用'),
        });
        this.init();
      } catch (e) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    togglePermission() {
      if (this.isPreDeployCommandDisabled) return;
      if (!this.configInfo.enabled) {
        this.configInfo.loaclEnabled = !this.configInfo.loaclEnabled;
        this.$nextTick(() => {
          if (this.configInfo.loaclEnabled) this.showEdit();
        });
      } else {
        this.$bkInfo({
          width: 500,
          title: `${this.$t('确认禁用模块')}${this.curAppModule.name}${this.$t('部署前置命令?')}`,
          subTitle: this.$t('禁用后，部署预发布环境、生产环境时都不会再执行该命令'),
          maskClose: true,
          confirmFn: () => {
            this.closeCommand();
          },
        });
      }
    },
    isReadOnlyRow(rowIndex) {
      return !_.includes(this.editRowList, rowIndex);
    },
    editingRowToggle(rowIndex) {
      // 点击切换状态(x)
      if (_.includes(this.editRowList, rowIndex)) {
        this.editRowList.pop(rowIndex);
      } else {
        this.editRowList.push(rowIndex);
        this.$refs[`varItem${rowIndex}`][0].focus();
      }
    },
    updateConfigVar(index) {
      const params = {
        procfile: [
          ...this.commandList,
        ],
      };
      this.requestCommand(this.$t('修改'), params, '');
      this.editRowList.pop(index);
    },
    deleteConfigVar(itemName) {
      this.commandList.splice(this.commandList.findIndex(v => v.name === itemName), 1);
      const params = {
        procfile: [...this.commandList],
      };
      this.requestCommand(this.$t('删除'), params, '');
    },
    // 添加启动命令
    createConfigVar() {
      const { name, command } = this.newVarConfig;
      const params = {
        procfile: [
          ...this.commandList,
        ],
      };
      const valueOf = this.commandList.findIndex(v => v.name === name);
      if (valueOf === -1) {
        params.procfile.unshift({ name, command });
        this.$refs.validate2.validate().then(() => {
          this.requestCommand(this.$t('添加'), params);
        });
      } else {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('重复命令'),
        });
      }
    },
    requestCommand(key, params, type = 'add') {
      this.$http.post(`${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/deploy_config/procfile/`, params).then((res) => {
        // 请求成功，返回当前添加的数据(根据添加数据决定)
        if (res.procfile) {
          this.$paasMessage({
            theme: 'success',
            message: this.$t('命令{key}成功', { key }),
          });
          if (type === 'add') this.commandList.push(params.procfile[0]);
          this.newVarConfig.name = '';
          this.newVarConfig.command = '';
        } else {
          this.$paasMessage({
            theme: 'error',
            message: this.$t('{key}失败', { key }),
          });
        }
      });
    },
    skip() {
      this.$router.push({
        name: 'appEntryConfig',
      });
    },
    inputFocusFun() {
      if (this.$route.query.from) {
        this.$refs.serverInput.focus();
      }
    },
  },
};
</script>
<style lang="scss">
    .ps-switcher-wrapper {
      &.disabled::before {
        cursor: not-allowed;
      }
      &.start-command-cls {
        margin-left: 0;
      }
    }
    .config-warp {
        padding: 20px;
        .info{
            color: #979ba5;
            font-size: 12px;
        }
        .command{
            color: #63656E;
            font-size: 14px;
        }
        .config-button{
            position: absolute;
            right: -80px;
            top: 7px;
        }
        .edit-disabled{
            cursor: not-allowed !important;
        }
    }
    .info-special-form {
        td {
            border: none;
        }
    }
    .ps-table-width-overflowed
    /deep/ .info-special-form.bk-form.bk-inline-form .bk-form-input[readonly]:nth-of-type(1) {
        background-color: #dcdee5 !important;
    }
    .mt-minus {
        margin-top: -10px;
        color: #979ba5;
        span {
            color: #3A84FF;
            &:hover {
                cursor: pointer;
            }
        }
    }
    .paas-info-app-name-cls input {
        padding-right: 130px !important;
    }
</style>
