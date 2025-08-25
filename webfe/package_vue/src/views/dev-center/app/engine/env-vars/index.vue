<template lang="html">
  <div class="right-main">
    <app-top-bar
      :title="$t('环境配置')"
      :can-create="canCreateModule"
      :cur-module="curAppModule"
      :module-list="curAppModuleList"
    />
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="env-loading"
      :offset-top="20"
      class="app-container env-container card-style"
    >
      <section v-show="!isLoading">
        <div class="middle variable-main">
          <div
            v-if="isEdited && isReleased"
            class="mt20"
          >
            <div class="ps-alert ps-alert-plain fadeIn">
              <div class="ps-alert-icon">
                <i class="paasng-icon paasng-info-circle-shape" />
              </div>
              <div class="ps-alert-content">
                <h4>{{ $t('重新发布使改动生效') }}</h4>
                <div>
                  {{ $t('您刚刚修改了环境变量，改动将在应用下次部署时生效。') }}
                  <br />
                  {{ $t('或者，您也可以选择现在进行静默发布让改动生效，服务将不会受到任何影响。') }}
                </div>
              </div>
              <div
                class="spacing-x2"
                style="border-bottom: solid 1px #e6e9ea"
              />
              <div
                class="row spacing-x2"
                style="margin-bottom: 0"
              >
                <div class="col-md-100">
                  <div class="ps-btn-group">
                    <button
                      class="ps-btn ps-btn-default ps-btn-l"
                      @click="releaseEnv(globalEnvName)"
                    >
                      {{ $t('发布到当前所有环境') }}
                    </button>

                    <dropdown
                      ref="releaseDropDown"
                      :options="{ position: 'bottom right', remove: 'click' }"
                    >
                      <button
                        slot="trigger"
                        class="ps-btn ps-btn-default ps-btn-l ps-btn-dropdown p10"
                      >
                        <i class="paasng-icon paasng-angle-down" />
                      </button>

                      <div slot="content">
                        <ul class="ps-list-group-link spacing-x0">
                          <li>
                            <a
                              v-if="isEnvAvailable('stag')"
                              @click="releaseEnv('stag')"
                            >
                              {{ $t('仅发布到预发布环境') }}
                            </a>
                          </li>
                          <li>
                            <a
                              v-if="isEnvAvailable('prod')"
                              @click="releaseEnv('prod')"
                            >
                              {{ $t('仅发布到生产环境') }}
                            </a>
                          </li>
                        </ul>
                      </div>
                    </dropdown>
                  </div>
                  <a
                    class="ps-btn ps-btn-l ps-btn-link spacing-h-x2"
                    @click="setEditedStatus(false)"
                  >
                    {{ $t('跳过，以后手动发布') }}
                  </a>
                </div>
              </div>
            </div>
          </div>

          <section
            v-if="curAppModule.source_origin !== GLOBAL.APP_TYPES.IMAGE"
            class="mb35 pt15"
          >
            <div class="ps-top-card mb10">
              <p class="main-title">
                {{ $t('自定义运行时') }}
              </p>
              <p class="desc">
                {{ $t('调整应用使用的基础镜像、构建工具包，修改后重新部署该模块生效') }}
              </p>
            </div>

            <table class="ps-table ps-table-border mt20 ps-edit-form">
              <tr>
                <td
                  style="width: 150px"
                  class="has-right-border"
                >
                  {{ $t('基础镜像') }}
                </td>
                <td style="width: 720px">
                  {{ runtimeImageText || '--' }}
                </td>
              </tr>
              <tr>
                <td class="has-right-border">
                  {{ $t('构建工具') }}
                </td>
                <td>
                  <template v-if="runtimeBuildTexts.length">
                    <p
                      v-for="(build, index) of runtimeBuildTexts"
                      :key="index"
                      :class="{ 'builder-item': runtimeBuildTexts.length > 1 }"
                    >
                      {{ build.name }}
                    </p>
                  </template>
                  <template v-else>
                    <p style="line-height: 20px">--</p>
                  </template>
                </td>
              </tr>
            </table>

            <bk-button
              theme="primary"
              class="mt10"
              @click="handleShowRuntimeDialog"
            >
              {{ $t('修改运行时配置') }}
            </bk-button>
          </section>

          <section class="mt20">
            <div class="ps-top-card mb15">
              <p class="main-title">
                {{ $t('环境变量配置') }}
              </p>
              <p class="desc">
                <!-- <a class="link-a" :href="GLOBAL.DOC.ENV_VAR_INLINE" target="_blank"> {{ $t('文档：什么是内置环境变量？') }} </a> -->
                {{ $t('环境变量可以用来改变应用在不同环境下的行为；除自定义环境变量外，平台也会写入内置环境变量。') }}
                <span
                  class="built-in-env"
                  @click="handleShoEnvDialog"
                >
                  {{ $t('查看内置环境变量') }}
                </span>
              </p>
              <p
                v-if="!canModifyEnvVariable"
                class="desc"
              >
                <bk-alert type="error">
                  <div slot="title">
                    <span v-if="curAppInfo.application.is_plugin_app">
                      {{ $t('应用已迁移到插件开发中心，本页面仅做展示用，如需操作请到') }}
                      <router-link
                        :to="{
                          name: 'pluginDeployEnv',
                          params: { id: curAppCode, pluginTypeId: 'bksaas' },
                        }"
                      >
                        {{ $t('插件开发- 配置管理页面') }}
                      </router-link>
                      {{ $t('。') }}
                    </span>
                    <span v-else>
                      {{ $t('当前应用不支持配置环境变量。') }}
                    </span>
                  </div>
                </bk-alert>
              </p>
            </div>
          </section>
        </div>
        <!-- 环境变量 -->
        <div class="top-box flex-row align-items-center justify-content-between mb-16">
          <div class="flex-row align-items-center">
            <bk-button
              class="mr10"
              :theme="'primary'"
              @click="handleAddVariable"
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
          </div>
          <div class="filter-list">
            <bk-dropdown-menu
              ref="largeDropdown"
              trigger="click"
              ext-cls="env-export-wrapper"
            >
              <bk-button
                slot="dropdown-trigger"
                :loading="exportLoading"
              >
                {{ $t('批量导入/导出') }}
              </bk-button>
              <ul
                slot="dropdown-content"
                class="bk-dropdown-list"
              >
                <li>
                  <a
                    href="javascript:;"
                    style="margin: 0"
                    :class="curModuleList.length < 1 || !canModifyEnvVariable ? 'is-disabled' : ''"
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
                <li>
                  <a
                    href="javascript:;"
                    style="margin: 0"
                    @click="handleExportToFile"
                  >
                    {{ $t('批量导出') }}
                  </a>
                </li>
              </ul>
            </bk-dropdown-menu>
          </div>
        </div>
        <!-- 环境变量列表 -->
        <EnvVarTable
          ref="envVarTableRef"
          :list="envVarList"
          :active="switchConfig.active"
          :loading="isVarLoading"
          @add="createConfigVar"
          @update="updateConfigVar"
          @delete="deleteConfigVar"
          @sort="handleSortChange"
          @batch-edit="() => (switchConfig.active = 'all')"
        />
      </section>
    </paas-content-loader>

    <bk-dialog
      v-model="runtimeDialogConf.visiable"
      width="850"
      :title="$t('修改运行时配置')"
      header-position="left"
      :theme="'primary'"
      :mask-close="false"
      :draggable="false"
      :close-icon="!isRuntimeUpdaing"
      render-directive="if"
      @confirm="updateRuntimeInfo"
      @cancel="handleHideRuntimeDialog"
    >
      <bk-form
        :label-width="localLanguage === 'en' ? 105 : 95"
        v-bkloading="{ isLoading: isRuntimeUpdaing, zIndex: 10 }"
      >
        <bk-form-item :label="$t('基础镜像:')">
          <bk-select
            v-model="runtimeDialogConf.image"
            searchable
            :clearable="false"
            @selected="handleImageChange"
          >
            <bk-option
              v-for="(option, index) in runtimeImageList"
              :id="option.image"
              :key="index"
              :name="option.name"
            >
              <div>
                {{ option.name }}
              </div>
            </bk-option>
          </bk-select>
        </bk-form-item>
        <bk-form-item ext-cls="customize-form-item-dashed">
          <div class="build-label">
            <span
              class="text"
              v-bk-tooltips="$t('构建工具会逐个进行构建，请注意构建工具的选择顺序')"
            >
              {{ $t('构建工具') }}
            </span>
          </div>
          <bk-transfer
            ext-cls="tool-transfer-wrapper-cls"
            :key="runtimeDialogConf.image"
            :target-list="targetListData"
            :source-list="runtimeBuildpacks"
            :title="[$t('可选的构建工具'), $t('选中的构建工具 (按选择顺序排序)')]"
            :display-key="'name'"
            :setting-key="'id'"
            @change="handleBuildpackChange"
          >
            <div
              slot="source-option"
              slot-scope="data"
              class="transfer-source-item"
              :data-id="data.id"
              v-bk-overflow-tips
            >
              {{ data.name }}
            </div>
            <div
              slot="target-option"
              slot-scope="data"
              class="transfer-source-item"
              :data-id="data.id"
              v-bk-overflow-tips
            >
              {{ data.name }}
            </div>
          </bk-transfer>
        </bk-form-item>
      </bk-form>
    </bk-dialog>

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
              v-for="option in curModuleList"
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
        <BuiltInEnvVarDisplay
          :app-code="appCode"
          :module-id="curModuleId"
        />
      </div>
    </bk-sideslider>
  </div>
</template>

<script>
import { cloneDeep, includes } from 'lodash';
import dropdown from '@/components/ui/Dropdown';
import tooltipConfirm from '@/components/ui/TooltipConfirm';
import appBaseMixin from '@/mixins/app-base-mixin';
import transferDrag from '@/mixins/transfer-drag';
import appTopBar from '@/components/paas-app-bar';
import BuiltInEnvVarDisplay from '@/components/builtIn-env-var-display';
import EnvVarTable from './env-var-table.vue';
import SwitchDisplay from '@/components/switch-display';

export default {
  components: {
    dropdown,
    tooltipConfirm,
    appTopBar,
    BuiltInEnvVarDisplay,
    EnvVarTable,
    SwitchDisplay,
  },
  mixins: [appBaseMixin, transferDrag],
  data() {
    return {
      envVarList: [],
      runtimeImageList: [],
      buildpackValueList: [],
      runtimeImage: '',
      runtimeBuild: [],
      isRuntimeUpdaing: false,
      availableEnv: [],
      isEdited: false,
      isReleased: false,
      newVarConfig: {
        key: '',
        value: '',
        env: 'stag',
        description: '',
      },
      varRules: {
        key: [
          {
            required: true,
            message: this.$t('KEY是必填项'),
            trigger: 'blur',
          },
          {
            max: 64,
            message: this.$t('不能超过64个字符'),
            trigger: 'blur',
          },
          {
            regex: /^[A-Z][A-Z0-9_]*$/,
            message: this.$t('只能以大写字母开头，仅包含大写字母、数字与下划线'),
            trigger: 'blur',
          },
        ],
        value: [
          {
            required: true,
            message: this.$t('VALUE是必填项'),
            trigger: 'blur',
          },
          {
            max: 2048,
            message: this.$t('不能超过2048个字符'),
            trigger: 'blur',
          },
        ],
        description: [
          {
            validator: (value) => {
              if (value === '') {
                return true;
              }
              return value.trim().length <= 200;
            },
            message: this.$t('不能超过200个字符'),
            trigger: 'blur',
          },
        ],
      },
      addingConfigVarEnv: 'stag',
      envSelectList: [
        { id: 'stag', text: this.$t('预发布环境') },
        { id: 'prod', text: this.$t('生产环境') },
        { id: '_global_', text: this.$t('所有环境') },
      ],
      editRowList: [],
      isLoading: true,
      isVarLoading: true,
      activeEnvTab: '',
      runtimeDialogConf: {
        visiable: false,
        image: '',
        buildpacks: [],
        buildpackValueList: [],
      },
      isDropdownShow: false,
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
      exportLoading: false,
      curFile: {},
      isFileTypeError: false,
      envSidesliderConf: {
        visiable: false,
      },
      targetListData: [],
      switchConfig: {
        list: [
          { name: 'all', label: this.$t('全部') },
          { name: '_global_', label: this.$t('所有环境') },
          { name: 'stag', label: this.$t('预发布环境') },
          { name: 'prod', label: this.$t('生产环境') },
        ],
        active: 'all',
      },
      allConflictedKeys: [],
    };
  },
  computed: {
    runtimeBuildpacks() {
      let result = [];
      const image = this.runtimeImageList.find((item) => item.image === this.runtimeDialogConf.image);
      const buildpacks = image ? [...image.buildpacks] : [];

      // 兼容穿梭框右侧排序问题，后续调整组件
      this.runtimeBuild.forEach((id) => {
        buildpacks.forEach((item, index) => {
          if (item.id === id) {
            result.push(item);
            buildpacks.splice(index, 1);
          }
        });
      });
      result = result.concat(buildpacks);

      return result;
    },
    runtimeImageText() {
      const result = this.runtimeImageList.find((item) => item.image === this.runtimeImage);
      if (result) {
        return result.name || result.image;
      }
      return '';
    },
    runtimeBuildTexts() {
      const builds = [];
      const image = this.runtimeImageList.find((item) => item.image === this.runtimeImage);
      const buildpacks = image ? image.buildpacks : [];
      this.runtimeBuild.forEach((item) => {
        buildpacks.forEach((pack) => {
          if (pack.id === item) {
            builds.push(pack);
          }
        });
      });
      return builds;
    },
    globalEnvName() {
      if (includes(this.availableEnv, 'stag') && includes(this.availableEnv, 'prod')) {
        return '_global_';
      }
      return this.availableEnv[0];
    },
    curModuleList() {
      return this.curAppModuleList.filter((item) => item.name !== this.curModuleId);
    },
    canModifyEnvVariable() {
      return this.curAppInfo && this.curAppInfo.feature.MODIFY_ENVIRONMENT_VARIABLE;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  watch: {
    $route() {
      this.init();
    },
  },
  created() {
    this.init();
  },
  methods: {
    handleImportFromFile() {
      if (!this.canModifyEnvVariable) {
        return;
      }
      this.importFileDialog.visiable = true;
    },
    handleCloneFromModule() {
      if (!this.canModifyEnvVariable) {
        return;
      }
      if (this.curModuleList.length < 1) {
        return;
      }
      this.exportDialog.visiable = true;
      this.moduleValue = this.curModuleList[0].id;
      this.curSelectModuleName = this.curModuleList[0].name;
      this.handleModuleSelected('', { name: this.curSelectModuleName });
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
            const errorMsg = errRes.detail;
            this.$paasMessage({
              theme: 'error',
              message: `${this.$t('获取环境变量失败')}，${errorMsg}`,
            });
          }
        )
        .finally(() => {
          this.exportLoading = false;
        });
    },

    invokeBrowserDownload(content, filename) {
      const a = document.createElement('a');
      const blob = new Blob([content], { type: 'text/plain' });
      a.download = filename;
      a.href = URL.createObjectURL(blob);
      a.click();
      a.remove();
      URL.revokeObjectURL(blob);
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
            this.loadConfigVar();
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
        this.catchErrorHandler(e);
      } finally {
        this.exportDialog.isLoading = false;
      }
    },
    handleReset() {
      this.activeEnvTab = '';
      this.newVarConfig.env = 'stag';
      this.loadConfigVar();
    },
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
        this.loadConfigVar();
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
    handleImportFileLeave() {
      this.curFile = {};
      this.isFileTypeError = false;
    },
    async init() {
      this.isLoading = true;
      this.setEditedStatus(false);
      this.curSortKey = 'created';
      this.loadConfigVar();
      this.fetchReleaseInfo();
      this.getAllImages();
      this.getRuntimeInfo();
    },
    fetchReleaseInfo() {
      // 这里分别调用预发布环境 和 生产环境的 API，只要有一个返回 200，isReleased 就要设置为 True
      this.$http
        .get(
          `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/envs/stag` +
            '/released_state/?with_processes=true'
        )
        .then(
          (response) => {
            this.isReleased = true;
            this.availableEnv.push('stag');
          },
          (errRes) => {
            console.error(errRes);
          }
        );

      this.$http
        .get(
          `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/envs/prod` +
            '/released_state/?with_processes=true'
        )
        .then(
          (response) => {
            this.isReleased = true;
            this.availableEnv.push('prod');
          },
          (errRes) => {
            console.error(errRes);
          }
        );
    },
    async getAllImages() {
      try {
        const res = await this.$store.dispatch('envVar/getAllImages', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });

        if (res.results) {
          res.results.forEach((item) => {
            item.name = `${item.slugbuilder.display_name || item.image} (${item.slugbuilder.description || '--'})`;

            item.buildpacks.forEach((item) => {
              item.name = `${item.display_name || item.name} (${item.description || '--'})`;
            });
          });
          this.runtimeImageList = res.results;
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    async getRuntimeInfo() {
      this.isRuntimeUpdaing = true;
      try {
        const res = await this.$store.dispatch('envVar/getRuntimeInfo', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.runtimeBuild = [];
        this.runtimeImage = res.image ? res.image : '';
        if (res.buildpacks) {
          this.runtimeBuild = res.buildpacks.map((item) => item.id);
          this.targetListData = cloneDeep(this.runtimeBuild);
          this.curBuildpacks = cloneDeep(this.runtimeBuild);
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          this.isRuntimeUpdaing = false;
        }, 500);
      }
    },
    async updateRuntimeInfo() {
      try {
        this.isRuntimeUpdaing = true;

        if (!this.runtimeDialogConf.image) {
          this.$paasMessage({
            theme: 'error',
            message: this.$t('请选择基础镜像！'),
          });
          this.$nextTick(() => {
            this.isRuntimeUpdaing = false;
          });
          return false;
        }
        // 使用拖拽排序后的数据
        const buildpacksIds = this.mixinTargetBuildpackIds || this.runtimeDialogConf.buildpacks;

        await this.$store.dispatch('envVar/updateRuntimeInfo', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          data: {
            image: this.runtimeDialogConf.image,
            buildpacks_id: buildpacksIds,
          },
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('保存成功'),
        });
        this.getRuntimeInfo();
        this.runtimeImage = this.runtimeDialogConf.image;
        this.runtimeBuild = this.runtimeDialogConf.buildpacks;
        this.runtimeDialogConf.visiable = false;
        this.isRuntimeUpdaing = false;
      } catch (e) {
        this.isRuntimeUpdaing = false;
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },
    // 获取环境变量冲突提示信息
    getConflictMessage(key) {
      const conflictItem = this.allConflictedKeys.find((item) => item.key === key);

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
    async getConflictInfo() {
      try {
        const res = await this.$store.dispatch('envVar/getConflictInfo', {
          appCode: this.appCode,
        });
        return res || [];
      } catch (e) {
        return [];
      }
    },
    // 获取环境变量
    async loadConfigVar() {
      this.isVarLoading = true;
      try {
        if (!this.allConflictedKeys?.length) {
          this.allConflictedKeys = await this.getConflictInfo();
        }
        const res = await this.$store.dispatch('envVar/getEnvVariables', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          orderBy: this.curSortKey,
        });
        if (this.activeEnvTab === '') {
          this.envVarList = [...res];
        } else {
          this.envVarList = res.filter((envVar) => envVar.environment_name === this.activeEnvTab);
        }
        this.envVarList = this.envVarList.map((item) => ({
          ...item,
          // 与内置环境变量冲突提示
          conflict: this.getConflictMessage(item.key),
        }));
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isVarLoading = false;
        this.isLoading = false;
      }
    },
    isEnvAvailable(envName) {
      return includes(this.availableEnv, envName);
    },
    // 环境变量错误处理
    handleEnvVarError(operation, error) {
      this.$paasMessage({
        theme: 'error',
        message: `${this.$t(`${operation}环境变量失败`)}，${error.message || error.detail}`,
      });
    },
    // 环境变量操作成功处理
    handleEnvVarSuccess(operation, data = null) {
      this.$paasMessage({
        theme: 'success',
        message: this.$t(`${operation}环境变量成功`),
      });
      this.setEditedStatus(true);
      this.loadConfigVar();
      // 取消编辑状态
      if (data) {
        this.$refs.envVarTableRef?.setEditingStatus(data, false);
      }
    },
    // 更新环境变量
    async updateConfigVar(data) {
      try {
        await this.$store.dispatch('envVar/updateEnvVariable', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          varId: data.id,
          data: data,
        });
        this.handleEnvVarSuccess('修改', data);
      } catch (e) {
        this.handleEnvVarError('修改', e, data);
      }
    },
    // 添加环境变量
    async createConfigVar(data) {
      try {
        await this.$store.dispatch('envVar/createdEnvVariable', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          data,
        });
        this.handleEnvVarSuccess('添加', data);
      } catch (e) {
        this.handleEnvVarError('添加', e, data);
      }
    },
    // 删除单个环境变量
    async deleteConfigVar(row) {
      try {
        await this.$store.dispatch('envVar/deleteEnvVariable', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          varId: row.id,
        });
        this.handleEnvVarSuccess('删除');
      } catch (e) {
        this.handleEnvVarError('删除', e);
      }
    },
    releaseEnv(envName) {
      this.$refs.releaseDropDown.close();
      this.$http
        .post(
          `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/envs/${envName}/releases/`
        )
        .then(
          (response) => {
            this.$paasMessage({
              theme: 'success',
              message: this.$t('发布提交成功，请在进程管理查看发布情况'),
            });
          },
          (errRes) => {
            const errorMsg = errRes.message;
            this.$paasMessage({
              theme: 'error',
              message: errorMsg,
            });
          }
        );
      this.setEditedStatus(false);
    },
    // 设置 change 状态
    setEditedStatus(flag) {
      this.isEdited = flag;
    },
    async handleShowRuntimeDialog() {
      this.runtimeDialogConf.visiable = true;
      // 获取选择列表
      await this.getRuntimeInfo();
      this.runtimeDialogConf.image = this.runtimeImage;
      this.runtimeDialogConf.buildpacks = this.runtimeBuild;
      this.runtimeDialogConf.buildpackValueList = this.runtimeBuild;

      this.mixinTargetBuildpackIds = null;
      // 绑定拖拽事件
      this.$nextTick(() => {
        this.transferDragInit();
      });
    },

    // 拖拽初始化
    transferDragInit() {
      const targetLiClass = '.tool-transfer-wrapper-cls .target-list .content li';
      // 设置拖拽prop
      this.mixinSetDraggableProp(targetLiClass);
      // 目标容器拖拽
      this.mixinBindDragEvent(
        document.querySelector('.tool-transfer-wrapper-cls .target-list .content'),
        targetLiClass
      );
    },

    // 数据还原
    handleHideRuntimeDialog() {
      setTimeout(() => {
        this.targetListData = cloneDeep(this.curBuildpacks);
      }, 200);
    },

    handleBuildpackChange(listEl, targetList, targetValueList) {
      this.runtimeDialogConf.buildpacks = targetValueList;
      this.$nextTick(() => {
        this.transferDragInit();
      });
    },

    handleImageChange() {
      this.runtimeDialogConf.buildpacks = [];
      this.runtimeDialogConf.buildpackValueList = [];
    },

    handleShoEnvDialog() {
      this.envSidesliderConf.visiable = true;
    },

    // 添加环境变量
    handleAddVariable() {
      this.$refs.envVarTableRef.add();
    },

    // 处理排序变化
    handleSortChange(sortKey) {
      this.curSortKey = sortKey;
      this.loadConfigVar();
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

<style lang="scss" scoped>
@import '~@/assets/css/mixins/ellipsis.scss';
.env-container {
  background: #fff;
  padding: 0 24px 24px;
  margin-top: 16px;
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
  color: #3a84ff;
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
  height: 100%;
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

/* 穿梭框样式设置 */
.tool-transfer-wrapper-cls .transfer-source-item {
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}
.customize-form-item-dashed {
  :deep(.bk-form-content) {
    position: relative;
  }
  .build-label {
    text-align: right;
    width: 150px;
    padding-right: 24px;
    position: absolute;
    left: -150px;
    top: 0;
    .text {
      padding-bottom: 2px;
      border-bottom: 1px dashed #666;
    }
  }
}
</style>

<style lang="scss">
.tool-transfer-wrapper-cls .target-list .content li.moving {
  background: transparent;
  color: transparent;
  border: 1px dashed #ccc;
}
</style>
