<template>
  <div class="env-container">
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="deploy-env-loading"
      :is-transition="false"
      :offset-top="0"
      :offset-left="0"
      class="middle"
    >
      <section v-show="!isLoading">
        <bk-alert type="info">
          <span slot="title">
            {{ $t('环境变量可以用来改变应用在不同环境下的行为；除自定义环境变量外，平台也会写入内置环境变量。') }}
            <span
              class="built-in-env"
              @click="handleShoEnvDialog"
            >
              {{ $t('查看内置环境变量') }}
            </span>
          </span>
        </bk-alert>
        <div class="flex-row align-items-center justify-content-between mt-16">
          <div class="left-filter flex-row align-items-center">
            <template v-if="!isBatchEditing">
              <bk-button
                :theme="'primary'"
                class="mr8"
                @click="handleAddSingleVariable"
              >
                <i class="paasng-icon paasng-plus-thick" />
                {{ $t('新增环境变量') }}
              </bk-button>
              <SwitchDisplay
                :list="switchConfig.list"
                :active="switchConfig.active"
                :has-icon="false"
                :has-count="false"
                @change="($event) => (switchConfig.active = $event.name)"
              />
            </template>
          </div>
          <div class="right flex-row align-items-center">
            <bk-button
              v-if="!isBatchEditing"
              :theme="'default'"
              class="export-btn-cls mr10"
              :outline="true"
              @click="handleBatchEdit"
            >
              {{ $t('批量编辑') }}
            </bk-button>
            <bk-dropdown-menu
              ref="largeDropdown"
              trigger="click"
              ext-cls="env-export-wrapper"
            >
              <bk-button
                slot="dropdown-trigger"
                class="mr10"
              >
                <i class="paasng-icon paasng-upload mr6"></i>
                {{ $t('导入') }}
              </bk-button>
              <ul
                slot="dropdown-content"
                class="bk-dropdown-list"
              >
                <li>
                  <a
                    href="javascript:;"
                    style="margin: 0"
                    :class="addedModuleList.length < 1 || !canModifyEnvVariable ? 'is-disabled' : ''"
                    @click="handleCloneFromModule"
                  >
                    {{ $t('从模块导入') }}
                  </a>
                </li>
                <li>
                  <a
                    href="javascript:;"
                    style="margin: 0"
                    :class="!canModifyEnvVariable ? 'is-disabled' : ''"
                    @click="handleImportFromFile"
                  >
                    {{ $t('从文件导入') }}
                  </a>
                </li>
              </ul>
            </bk-dropdown-menu>
            <bk-button
              :theme="'default'"
              :outline="true"
              class="export-btn-cls"
              @click="handleExportToFile"
            >
              <i class="paasng-icon paasng-import mr6"></i>
              {{ $t('导出') }}
            </bk-button>
          </div>
        </div>
        <bk-alert
          type="success"
          class="mt-16"
          v-if="isDeployEnvVarChange"
        >
          <span slot="title">
            {{ $t('环境变量{t}成功，修改将在应用下次部署时生效。', { t: envVarChangeText }) }}
            <bk-button
              :theme="'primary'"
              text
              size="small"
              class="to-deploy-btn"
              @click="handleToDeploy"
            >
              {{ $t('去部署') }}
            </bk-button>
          </span>
        </bk-alert>

        <!-- 环境变量表格 -->
        <EnvVarTable
          class="mt-16"
          ref="envVarTableRef"
          :list="envLocalVarList"
          :active="switchConfig.active"
          :loading="isTableLoading"
          :show-empty="envLocalVarList.length > 1"
          @add="createdEnvVariable"
          @update="updateEnvVariable"
          @delete="handleSingleDelete"
          @sort="handleSortChange"
          @batch-edit="() => (switchConfig.active = 'all')"
        >
          <template #append>
            <template v-if="!envLocalVarList.length">
              <!-- 存在预设环境变量空状态 -->
              <div
                v-if="varPresetlLength"
                class="exception-wrap-cls file"
              >
                {{ $t('暂无数据') }}
              </div>
              <!-- 无预设环境变量空状态 -->
              <bk-exception
                v-else
                class="exception-wrap-cls"
                type="empty"
                scene="part"
              >
                <span>{{ $t('暂无数据') }}</span>
              </bk-exception>
            </template>
            <!-- 应用描述文件 -->
            <app-description-file
              v-if="isShowPresetVariableList"
              :env-vars="envLocalVarList"
              :active-env="switchConfig.active"
              :order-by="curSortKey"
              @var-preset-length="varPresetlLength = $event"
            />
          </template>
        </EnvVarTable>

        <div
          class="mt-24"
          v-if="isBatchEditing"
        >
          <bk-button
            :theme="'primary'"
            @click="batchEditSaveValidation"
          >
            {{ $t('保存') }}
          </bk-button>
          <bk-button
            class="ml8"
            @click="batchEditCancel"
          >
            {{ $t('取消') }}
          </bk-button>
        </div>
      </section>
    </paas-content-loader>

    <bk-sideslider
      :is-show.sync="envSidesliderConf.visiable"
      :width="800"
      :title="$t('内置环境变量')"
      :quick-close="true"
    >
      <div
        slot="content"
        class="slider-env-content"
      >
        <builtIn-env-var-display :app-code="appCode" />
      </div>
    </bk-sideslider>

    <bk-dialog
      v-model="exportDialog.visiable"
      :title="$t('从其它模块导入环境变量')"
      :header-position="exportDialog.headerPosition"
      :width="exportDialog.width"
      @after-leave="handleAfterLeave"
    >
      <div>
        <div class="paas-env-var-export">
          <label class="title">{{ $t('模块：') }}</label>
          <bk-select
            v-model="moduleValue"
            :disabled="false"
            :clearable="false"
            searchable
            style="flex: 0 0 390px"
            @selected="handleModuleSelected"
          >
            <bk-option
              v-for="option in addedModuleList"
              :id="option.id"
              :key="option.id"
              :name="option.name"
            />
          </bk-select>
        </div>
        <div
          v-bkloading="{ isLoading: exportDialog.isLoading, opacity: 1 }"
          class="export-by-module-tips"
        >
          <p
            v-if="exportDialog.count"
            style="line-height: 20px"
          >
            【{{ curSelectModuleName }}】 {{ $t('模块共有') }} {{ exportDialog.count }}
            {{ $t('个环境变量，将增量更新到当前') }} 【{{ curModuleId }} 】{{ $t('模块') }}
          </p>
          <p v-else>【{{ curSelectModuleName }}】 {{ $t('模块暂无环境变量，请选择其它模块') }}</p>
        </div>
      </div>
      <div slot="footer">
        <bk-button
          theme="primary"
          class="mr10"
          :disabled="exportDialog.count < 1"
          :loading="exportDialog.loading"
          @click="handleExportConfirm"
        >
          {{ $t('确定导入') }}
        </bk-button>
        <bk-button @click="handleExportCancel">
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>

    <bk-dialog
      v-model="importFileDialog.visiable"
      :header-position="importFileDialog.headerPosition"
      :loading="importFileDialog.loading"
      :width="importFileDialog.width"
      :ok-text="$t('确定导入')"
      ext-cls="paas-env-var-upload-dialog"
      @after-leave="handleImportFileLeave"
    >
      <div
        slot="header"
        class="header"
      >
        {{ $t('从文件导入环境变量到') }}【
        <span
          class="title"
          :title="curModuleId"
        >
          {{ curModuleId }}
        </span>
        】{{ $t('模块') }}
      </div>
      <div>
        <div class="download-tips">
          <span>
            <i class="paasng-icon paasng-exclamation-circle" />
            {{ $t('请先下载模板，按格式修改后点击“选择文件”批量导入') }}
          </span>
          <bk-button
            text
            theme="primary"
            size="small"
            style="line-height: 40px"
            @click="handleDownloadTemplate"
          >
            {{ $t('下载模板') }}
          </bk-button>
        </div>
        <div class="upload-content">
          <p><i class="paasng-icon paasng-file-fill file-icon" /></p>
          <p>
            <bk-button
              text
              theme="primary"
              ext-cls="env-var-upload-btn-cls"
              @click="handleTriggerUpload"
            >
              {{ $t('选择文件') }}
            </bk-button>
          </p>
          <p
            v-if="curFile.name"
            class="cur-upload-file"
          >
            {{ $t('已选择文件：') }} {{ curFile.name }}
          </p>
          <p
            v-if="isFileTypeError"
            class="file-error-tips"
          >
            {{ $t('请选择yaml文件') }}
          </p>
        </div>

        <input
          ref="upload"
          type="file"
          style="position: absolute; width: 0; height: 0"
          @change="handleStartUpload"
        />
      </div>
      <div slot="footer">
        <bk-button
          theme="primary"
          class="mr10"
          :loading="importFileDialog.loading"
          :disabled="!curFile.name"
          @click="handleImportFileConfirm"
        >
          {{ $t('确定导入') }}
        </bk-button>
        <bk-button @click="handleImportFileCancel">
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-dialog>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import builtInEnvVarDisplay from '@/components/builtIn-env-var-display';
import AppDescriptionFile from './app-description-file.vue';
import EnvVarTable from '../env-vars/env-var-table.vue';
import SwitchDisplay from '@/components/switch-display';

export default {
  components: {
    builtInEnvVarDisplay,
    AppDescriptionFile,
    EnvVarTable,
    SwitchDisplay,
  },
  mixins: [appBaseMixin],
  props: {
    // 组件内部按钮操作
    isComponentBtn: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      curItem: {},
      envLocalVarList: [],
      isLoading: true,
      isTableLoading: true,
      envSidesliderConf: {
        visiable: false,
      },
      curSortKey: 'created',
      exportDialog: {
        visiable: false,
        width: 480,
        headerPosition: 'center',
        loading: false,
        isLoading: false,
        count: 0,
      },
      importFileDialog: {
        visiable: false,
        width: 540,
        headerPosition: 'center',
        loading: false,
      },
      moduleValue: '',
      curSelectModuleName: '',
      curFile: {},
      isFileTypeError: false,
      isShowPresetVariableList: false,
      varPresetlLength: 0,
      isDeployEnvVarChange: false,
      envVarChangeText: '',
      // 加密后 Value 的默认值。与接口一致
      DEFAULT_ENCRYPTED_VALUE: '******',
      switchConfig: {
        list: [
          { name: 'all', label: this.$t('全部') },
          { name: '_global_', label: this.$t('所有环境') },
          { name: 'stag', label: this.$t('预发布环境') },
          { name: 'prod', label: this.$t('生产环境') },
        ],
        active: 'all',
      },
      // 是否开启批量编辑
      isBatchEditing: false,
    };
  },
  computed: {
    canModifyEnvVariable() {
      return this.curAppInfo && this.curAppInfo.feature.MODIFY_ENVIRONMENT_VARIABLE;
    },

    addedModuleList() {
      return this.curAppModuleList.filter((item) => item.name !== this.curModuleId);
    },
  },
  created() {
    this.init();
  },
  methods: {
    async init() {
      this.isLoading = true;
      this.getEnvVarList();
    },

    showErrorMessage(e) {
      this.$paasMessage({
        theme: 'error',
        message: `${this.$t('获取环境变量失败')}，${e.message || e.detail}`,
      });
    },

    // 获取环境变量冲突提示
    getConflictMessage(conflictedKeys, key) {
      const conflictItem = conflictedKeys.find((item) => item.key === key);

      if (!conflictItem) return {};

      const { conflicted_detail, override_conflicted, conflicted_source } = conflictItem;
      const basicText = override_conflicted ? this.$t('当前配置将覆盖内置变量') : this.$t('当前配置不生效');
      const conflictSourceMessage =
        conflicted_source === 'builtin_addons'
          ? this.$t('和 {k} 增强服务的环境变量冲突', { k: conflicted_detail })
          : this.$t('和平台的内置环境变量冲突');

      return {
        message: `${basicText}，${conflictSourceMessage}`,
        overrideConflicted: override_conflicted,
      };
    },

    // 获取冲突的环境变量
    async getConflictedEnvVariables() {
      try {
        const res = await this.$store.dispatch('envVar/getConflictedEnvVariables', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        return res || [];
      } catch (e) {
        return [];
      }
    },

    // 获取环境列表
    async getEnvVarList(isUpdate = true) {
      this.isTableLoading = true;
      try {
        const conflictedKeys = await this.getConflictedEnvVariables();
        const res = await this.$store.dispatch('envVar/getEnvVariables', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          orderBy: this.curSortKey,
        });
        if (isUpdate) {
          this.envLocalVarList = [...res];
        }
        this.envLocalVarList = res.map((item) => ({
          ...item,
          isEdit: false, // 取消编辑态
          conflict: conflictedKeys.length > 0 ? this.getConflictMessage(conflictedKeys, item.key) : {},
          id: item.id || res.find((i) => i.key === item.key)?.id,
        }));
      } catch (e) {
        this.showErrorMessage(e);
      } finally {
        this.isShowPresetVariableList = true;
        this.isTableLoading = false;
        this.isLoading = false;
      }
    },

    // 批量编辑保存
    async batchEditSaveValidation() {
      try {
        const batchData = await this.$refs.envVarTableRef.saveBatchEdit();
        this.batchConfigVars(batchData);
      } catch (e) {
        console.error(e);
      }
    },

    // 新增加单个环境变量
    async createdEnvVariable(data) {
      try {
        await this.$store.dispatch('envVar/createdEnvVariable', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          data: data,
        });
        this.handleEnvVarChange(this.$t('添加'));
        this.getEnvVarList();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('添加环境变量失败')}，${e.message}`,
        });
      }
    },

    // 修改加单个环境变量
    async updateEnvVariable(data) {
      try {
        await this.$store.dispatch('envVar/updateEnvVariable', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          varId: data.id,
          data: data,
        });
        this.handleEnvVarChange(this.$t('修改'));
        this.getEnvVarList();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('修改环境变量失败')}，${e.message}`,
        });
      }
    },

    // 批量编辑保存
    async batchConfigVars(batchData) {
      try {
        await this.$store.dispatch('envVar/batchConfigVars', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          data: batchData,
        });
        // 操作对应tips
        let tipsType = batchData.length > this.envLocalVarList.length ? '添加' : '删除';
        if (batchData.length === this.envLocalVarList.length) {
          tipsType = '修改';
        }
        this.handleEnvVarChange(this.$t(tipsType));
        // 批量更新不打乱当前顺序，重新复制当前新建id
        this.getEnvVarList(false);
      } catch (error) {
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('添加环境变量失败')}，${error.message}`,
        });
      }
      this.isBatchEditing = false;
    },

    handleShoEnvDialog() {
      this.envSidesliderConf.visiable = true;
    },

    // 开启批量编辑
    handleBatchEdit() {
      this.$refs.envVarTableRef.batchEdit();
      this.isBatchEditing = true;
    },

    handleCloneFromModule() {
      if (!this.canModifyEnvVariable) {
        return;
      }
      if (this.addedModuleList.length < 1) {
        return;
      }
      this.exportDialog.visiable = true;
      this.moduleValue = this.addedModuleList[0].id;
      this.curSelectModuleName = this.addedModuleList[0].name;
      this.handleModuleSelected('', { name: this.curSelectModuleName });
    },

    // 获取其他模块的环境变量
    async handleModuleSelected(value, { name }) {
      this.curSelectModuleName = name;
      this.exportDialog.isLoading = true;
      try {
        const response = await this.$store.dispatch('envVar/getEnvVariables', {
          appCode: this.appCode,
          moduleId: name,
          orderBy: '-created',
        });
        this.exportDialog.count = (response || []).length;
      } catch (e) {
        this.showErrorMessage(e);
      } finally {
        this.exportDialog.isLoading = false;
      }
    },

    // 导入其他模块的环境变量
    async handleExportConfirm() {
      this.exportDialog.loading = true;
      try {
        const res = await this.$store.dispatch('envVar/exportModuleEnv', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          sourceModuleName: this.curSelectModuleName,
        });
        const createNum = res.create_num;
        const overwritedNum = res.overwrited_num;
        const ignoreNum = res.ignore_num;
        this.isEdited = createNum > 0 || overwritedNum > 0;
        const message = (() => {
          const numStr = `${Number(Boolean(createNum))}${Number(Boolean(overwritedNum))}${Number(Boolean(ignoreNum))}`;
          let messageText = '';
          switch (numStr) {
            case '111':
              messageText = `${this.$t('导入成功，新增 ')}${createNum}${this.$t(
                '个变量，更新'
              )}${overwritedNum} ${this.$t('个变量，忽略')} ${ignoreNum} ${this.$t('个变量')}`;
              break;
            case '110':
              messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t(
                '个变量，更新'
              )} ${overwritedNum} ${this.$t('个变量')}`;
              break;
            case '100':
              messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t('个变量')}`;
              break;
            case '101':
              messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t(
                '个变量，忽略'
              )} ${ignoreNum} ${this.$t('个变量')}`;
              break;
            case '011':
              messageText = `${this.$t('导入成功，更新')} ${overwritedNum} ${this.$t(
                '个变量，忽略'
              )} ${ignoreNum} ${this.$t('个变量')}`;
              break;
            case '010':
              messageText = `${this.$t('导入成功，更新')} ${overwritedNum} ${this.$t('个变量')}`;
              break;
            case '001':
              messageText = this.$t('所有环境变量都已在当前模块中，已全部忽略');
              break;
            default:
              messageText = `${this.$t('导入成功')}`;
          }
          return messageText;
        })();
        this.$paasMessage({
          theme: 'success',
          message,
        });
        this.handleExportCancel();
        this.getEnvVarList();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.exportDialog.loading = false;
      }
    },
    handleExportCancel() {
      this.exportDialog.visiable = false;
    },

    handleImportFileCancel() {
      this.importFileDialog.visiable = false;
    },

    handleAfterLeave() {
      this.moduleValue = '';
      this.curSelectModuleName = '';
      this.exportDialog.count = 0;
    },

    // 从文件导入
    handleImportFromFile() {
      if (!this.canModifyEnvVariable) {
        return;
      }
      this.importFileDialog.visiable = true;
    },

    handleExportToFile() {
      this.exportLoading = true;
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/config_vars/export/?order_by=${this.curSortKey}`;
      this.$http
        .get(url)
        .then(
          (response) => {
            this.invokeBrowserDownload(response, `bk_paas3_${this.appCode}_${this.curModuleId}_env_vars.yaml`);
          },
          (errRes) => {
            this.showErrorMessage(errRes);
          }
        )
        .finally(() => {
          this.exportLoading = false;
        });
    },

    handleImportFileLeave() {
      this.curFile = {};
      this.isFileTypeError = false;
    },

    handleDownloadTemplate() {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/config_vars/template/`;
      this.$http.get(url).then(
        (response) => {
          this.invokeBrowserDownload(response, 'bk_paas3_env_vars_import_template.yaml');
        },
        (errRes) => {
          const errorMsg = errRes.detail;
          this.$paasMessage({
            theme: 'error',
            message: `${this.$t('获取yaml模板失败')}，${errorMsg}`,
          });
        }
      );
    },

    handleTriggerUpload() {
      this.$refs.upload.click();
    },

    handleStartUpload(payload) {
      const files = Array.from(payload.target.files);
      const curFile = files[0];
      const fileExtension = curFile.name.substring(curFile.name.lastIndexOf('.') + 1);
      if (fileExtension !== 'yaml') {
        this.isFileTypeError = true;
        return;
      }
      this.isFileTypeError = false;
      this.curFile = curFile;
      this.$refs.upload.value = '';
    },

    handleImportFileConfirm() {
      this.importFileDialog.loading = true;
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/config_vars/import/`;
      const params = new FormData();
      params.append('file', this.curFile);
      this.$http
        .post(url, params)
        .then(
          (response) => {
            const createNum = response.create_num;
            const overwritedNum = response.overwrited_num;
            const ignoreNum = response.ignore_num;
            this.isEdited = createNum > 0 || overwritedNum > 0;
            const message = (() => {
              const numStr = `${Number(Boolean(createNum))}${Number(Boolean(overwritedNum))}${Number(
                Boolean(ignoreNum)
              )}`;
              let messageText = '';
              switch (numStr) {
                case '111':
                  messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t(
                    '个变量，更新'
                  )} ${overwritedNum} ${this.$t('个变量，忽略')} ${ignoreNum} ${this.$t('个变量')}`;
                  break;
                case '110':
                  messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t(
                    '个变量，更新'
                  )} ${overwritedNum} ${this.$t('个变量')}`;
                  break;
                case '100':
                  messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t('个变量')}`;
                  break;
                case '101':
                  messageText = `${this.$t('导入成功，新增')} ${createNum} ${this.$t(
                    '个变量，忽略'
                  )} ${ignoreNum} ${this.$t('个变量')}`;
                  break;
                case '011':
                  messageText = `${this.$t('导入成功，更新')} ${overwritedNum} ${this.$t(
                    '个变量，忽略'
                  )} ${ignoreNum} ${this.$t('个变量')}`;
                  break;
                case '010':
                  messageText = `${this.$t('导入成功，更新')} ${overwritedNum} ${this.$t('个变量')}`;
                  break;
                case '001':
                  messageText = this.$t('所有环境变量都已在当前模块中，已全部忽略');
                  break;
                default:
                  messageText = `${this.$t('导入成功')}`;
              }
              return messageText;
            })();
            this.$paasMessage({
              theme: 'success',
              message,
            });
            this.getEnvVarList();
          },
          (errRes) => {
            const errorMsg = errRes.detail;
            this.$paasMessage({
              theme: 'error',
              message: `${this.$t('从文件导入环境变量失败')}，${errorMsg}`,
            });
          }
        )
        .finally(() => {
          this.importFileDialog.loading = false;
          this.importFileDialog.visiable = false;
        });
    },

    // 处理下载
    invokeBrowserDownload(content, filename) {
      const a = document.createElement('a');
      const blob = new Blob([content], { type: 'text/plain' });
      a.download = filename;
      a.href = URL.createObjectURL(blob);
      a.click();
      a.remove();
      URL.revokeObjectURL(blob);
    },

    // 取消
    batchEditCancel() {
      this.$refs.envVarTableRef.batchCancel();
      this.isBatchEditing = false;
    },

    // 删除单个环境变量
    async handleSingleDelete(row) {
      try {
        await this.$store.dispatch('envVar/deleteEnvVariable', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          varId: row.id,
        });
        this.handleEnvVarChange(this.$t('删除'));
        this.getEnvVarList();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: `${this.$t('删除环境变量失败')}，${e.message}`,
        });
      }
    },
    // 新建环境变量模板
    handleAddSingleVariable() {
      this.$refs.envVarTableRef.add();
    },

    // key 表头排序
    handleSortChange(sortKey) {
      this.curSortKey = sortKey;
      this.getEnvVarList();
    },

    // 环境变量变更
    handleEnvVarChange(text, value = true) {
      this.envVarChangeText = text;
      this.isDeployEnvVarChange = value;
    },

    // 跳转部署管理
    handleToDeploy() {
      this.$router.push({
        name: 'cloudAppDeployManageStag',
        params: {
          id: this.appCode,
          isShowDeploy: true,
          deployModuleId: this.curModuleId,
        },
      });
    },
  },
};
</script>

<style media="screen">
.query-button {
  width: auto;
  padding-right: 30px;
}
</style>

<style lang="scss">
.ps-table-default {
  .bk-form-item {
    .bk-form-content {
      width: 100%;
      float: none !important;
      display: block !important;
    }
  }
}
</style>

<style lang="scss" scoped>
.env-container {
  padding: 0 20px 20px;
  min-height: 200px;
  .to-deploy-btn {
    height: auto;
    line-height: 1;
    padding: 0;
  }
}
.variable-instruction {
  font-size: 14px;
  color: #7b7d8a;
  padding: 15px 30px;
  line-height: 28px;
  border-bottom: 1px solid #eaeeee;
}

.paas-env-var-upload-dialog {
  .header {
    font-size: 24px;
    color: #313238;
  }
  .title {
    max-width: 150px;
    margin: 0;
    display: inline-block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    vertical-align: bottom;
  }
  .download-tips {
    display: flex;
    justify-content: space-between;
    padding: 0 10px;
    line-height: 40px;
    background: #fefaf2;
    font-size: 12px;
    color: #ffb400;
  }
}

a.is-disabled {
  color: #dcdee5 !important;
  cursor: not-allowed !important;
  &:hover {
    background: #fff !important;
  }
}

.upload-content {
  margin-top: 15px;
  text-align: center;
  .file-icon {
    font-size: 40px;
    color: #dae1e8;
  }
  .cur-upload-file {
    display: inline-block;
    line-height: 1;
    font-size: 12px;
    color: #3a84ff;
    border-bottom: 1px solid #3a84ff;
  }
  .file-error-tips {
    display: inline-block;
    line-height: 1;
    font-size: 12px;
    color: #ff4d4d;
  }
}

.ps-table-width-overflowed {
  width: 100%;
  margin-left: 0;

  td {
    border-bottom: 0;
    padding: 15px 0 0 0;
  }

  .desc-form-content {
    display: inline-block;
    padding: 0 10px;
    width: 100%;
    height: 32px;
    border: 1px solid #dcdee5;
    border-radius: 2px;
    text-align: left;
    font-size: 12px;
    color: #63656e;
    overflow: hidden;
    background-color: #fafbfd;
    vertical-align: middle;
    cursor: default;
  }
  .bk-inline-form {
    display: flex;
  }
}

.variable-main {
  border-bottom: 0;

  h3 {
    line-height: 1;
    padding: 10px 0;
  }

  .ps-alert-content {
    color: #666;
  }
}

.variable-input {
  margin-right: 10px;

  input {
    height: 36px;
  }
}

.variable-select {
  margin-right: 10px;
}

.variable-operation {
  font-size: 0;

  button {
    width: 72px;
    line-height: 18px;
    -webkit-box-sizing: border-box;
    -moz-box-sizing: border-box;
    -ms-box-sizing: border-box;
    box-sizing: border-box;
    -webkit-transition: 0s all;
    -moz-transition: 0s all;
    -ms-transition: 0s all;
    transition: 0s all;
  }

  a {
    &.paasng-delete {
      font-size: 16px;
    }

    &.paasng-check-1 {
      font-size: 15px;
    }
  }
}

.middle {
  > p {
    line-height: 46px;
  }
}

.variabletext {
  width: 100%;
  box-sizing: border-box;
  line-height: 30px;
  height: 34px;
}

.filter-list {
  position: relative;
  font-size: 0;
  letter-spacing: -5px;
  margin: 25px 0 5px 0;

  .label {
    position: relative;
    display: inline-block;
    top: 4px;
    letter-spacing: 0;
    font-size: 14px;
  }

  .reset-button {
    position: relative;
    top: 4px;
    padding-left: 10px;
  }

  .env-export-wrapper {
    position: absolute;
    right: 80px;
  }

  .env-sort-wrapper {
    position: absolute;
    left: 410px;
    .sort-icon {
      position: absolute;
      // width: 26px;
      font-size: 26px;
      left: 5px;
      top: 2px;
    }
    .text {
      padding-left: 15px;
    }
    a.active {
      background-color: #eaf3ff;
      color: #3a84ff;
    }
  }

  a {
    letter-spacing: 0;
    font-size: 14px;
    padding: 8px 20px;
    line-height: 14px;
    margin-right: 10px;

    &.ps-btn {
      border: 1px solid #ccc;
      color: #999;

      &:hover {
        border: 1px solid #3c96ff;
        color: #3c96ff;
      }
    }

    &.ps-btn-primary {
      background: #3c96ff;
      border: 1px solid #3a84ff;
      color: #fff;

      &:hover {
        color: #fff;
      }
    }
  }

  .env-sort-btn {
    position: absolute;
    right: 0;
    .sort-icon {
      position: absolute;
      font-size: 26px;
      left: 5px;
      top: 2px;
    }
    .text {
      padding-left: 15px;
    }
    &:hover {
      color: #3a84ff;
      border-color: #3a84ff;
    }
  }
}

.selectize-control * {
  cursor: pointer;
}

.editingEnvRow {
  color: #3a84ff;
}

.disabledButton:hover {
  cursor: pointer;
  color: #666;
  background: #fafafa;
}

.releasebg {
  padding: 0 20px 20px 20px;
  position: relative;
  border: solid 1px #e5e5e5;

  &-compact {
    padding-bottom: 5px;
  }

  .warningIcon {
    position: absolute;
    left: 20px;
    top: 28px;
    width: 24px;
    height: 24px;

    img {
      width: 100%;
    }
  }

  .warningText {
    margin-left: 10px;
    padding-bottom: 20px;
    position: relative;
    top: 0;
    right: 0;

    h2 {
      padding-left: 0;
    }

    &-compact {
      padding-bottom: 5px;
    }
  }
}

.ps-btn-xs {
  line-height: 34px;
}

.ps-form-control[readonly] {
  background-color: #fafafa;
}

.middle h4 {
  padding-top: 0;
}

.ps-alert h4 {
  margin: 0;
}

.ps-btn-dropdown,
.ps-btn-l {
  box-sizing: border-box;
  height: 36px;
}

.form-grid {
  display: flex;
}

.builder-item {
  padding: 0 10px;
  line-height: 20px;
  position: relative;

  &:before {
    content: '';
    font-size: 12px;
    position: absolute;
    left: 0;
    top: 8px;
    width: 3px;
    height: 3px;
    display: inline-block;
    background: #656565;
  }
}

.export-by-module-tips {
  padding: 4px 0 0 37px;
  line-height: 32px;
  color: #979ba5;
  font-size: 12px;
}

.paas-env-var-export {
  display: flex;
  justify-content: flex-start;
  .title {
    line-height: 30px;
  }
}

.link-a:hover {
  color: #699df4;
}

.img-exception {
  width: 300px;
}
.text-exception {
  color: #979ba5;
  font-size: 14px;
  text-align: center;
  margin-top: 14px;
}
.built-in-env {
  text-decoration: none !important;
  color: #3a84ff;

  &:hover {
    cursor: pointer;
  }
}

.slider-env-content {
  padding: 20px 24px;
  min-height: calc(100vh - 50px);
}
.env-title {
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 5px;
  color: #313238;
  line-height: 1;
}

.env-item {
  font-size: 12px;
  line-height: 24px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.desc-env {
  font-size: 12px;
  color: #979ba5;
  margin-bottom: 10px;
}

.env-table-icon {
  color: #c4c6cc;
  font-size: 14px;
  .icon {
    cursor: pointer;
    padding: 5px;
  }
}

.export-btn-cls {
  font-size: 12px;
}

.exception-wrap-cls {
  height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  &.file {
    height: 42px;
    font-size: 12px;
    color: #979ba5;
    border-bottom: 1px solid #dfe0e5;
  }
}
.variable-table-cls {
  /deep/ .bk-table-empty-block {
    display: none;
  }
}
.mr6 {
  margin-right: 6px;
}
.right {
  .paasng-upload,
  .paasng-download {
    font-size: 12px;
  }
}
.filter-action-list {
  display: flex;
  align-items: center;
  height: 32px;
  padding: 4px;
  border-radius: 2px;
  background: #f0f1f5;

  li {
    position: relative;
    user-select: none;
    height: 100%;
    line-height: 24px;
    font-size: 12px;
    color: #63656e;
    padding: 0 15px;
    cursor: pointer;

    &::before {
      position: absolute;
      top: 50%;
      left: 0;
      display: block;
      width: 1px;
      height: 12px;
      margin-top: -6px;
      background: #dcdee5;
      content: '';
    }
    &:first-child::before {
      height: 0;
    }

    &.active {
      color: #3a84ff;
      background: #fff;
      border-radius: 2px;

      &::before {
        background: #fff;
      }

      & + li::before {
        height: 0;
      }
    }
  }
}
</style>
