<template>
  <div class="mirror-main">
    <section class="mirror-info">
      <div class="header-wrapper mb20">
        <span :class="['build-title', { edit: isMirrorEdit }]">{{ $t('镜像信息') }}</span>
        <div
          class="edit-container"
          @click="handleEdit"
          v-if="!isMirrorEdit"
        >
          <i class="paasng-icon paasng-edit-2 pl10" />
          {{ $t('编辑') }}
        </div>
      </div>

      <!-- 查看态 -->
      <div
        class="content"
        v-if="!isMirrorEdit"
      >
        <div class="code-detail form-edit">
          <bk-form :model="mirrorData">
            <bk-form-item :label="`${$t('镜像仓库')}：`">
              <!-- 镜像托管模式 -->
              <template v-if="mirrorData.image_repository">
                {{ mirrorData.image_repository || '--' }}
              </template>
              <!-- 源码交付，平台产出镜像模式 -->
              <template v-else-if="mirrorData.env_image_repositories">
                <!-- 如果两个环境的镜像仓库是一样的，则只显示一个 -->
                <div v-if="mirrorData.env_image_repositories.prod == mirrorData.env_image_repositories.stag">
                  <span class="form-text">{{ mirrorData.env_image_repositories.prod }}</span>
                </div>
                <!-- 否则两个环境分别展示 -->
                <div v-else>
                  <div v-if="mirrorData.env_image_repositories.prod">
                    <span class="form-text">{{ mirrorData.env_image_repositories.prod }} （{{ $t('生产环境') }}）</span>
                  </div>
                  <div v-if="mirrorData.env_image_repositories.stag">
                    <span class="form-text">
                      {{ mirrorData.env_image_repositories.stag }} （{{ $t('预发布环境') }}）
                    </span>
                  </div>
                </div>
              </template>
              <template v-else>--</template>
            </bk-form-item>
            <bk-form-item :label="`${$t('镜像 tag 规则')}：`">
              <span class="form-text">
                {{ imageTag }}
              </span>
            </bk-form-item>
            <bk-form-item :label="`${$t('构建方式')}：`">
              <span class="form-text">
                {{ $t(methodType[mirrorData.build_method]) || '--' }}
              </span>
            </bk-form-item>
            <bk-form-item
              :label="`${$t('蓝盾流水线构建')}：`"
              v-if="curAppInfo.feature?.BK_CI_PIPELINE_BUILD"
            >
              <span class="form-text">
                {{ mirrorData.use_bk_ci_pipeline ? $t('已启用') : $t('未启用') }}
              </span>
            </bk-form-item>
            <!-- 蓝鲸 Buildpack -->
            <template v-if="mirrorData.build_method === 'buildpack'">
              <bk-form-item :label="`${$t('基础镜像')}：`">
                <span class="form-text">{{ baseImageText }}</span>
              </bk-form-item>
              <bk-form-item :label="`${$t('构建工具')}：`">
                <template v-if="!mirrorData.buildpacks?.length">--</template>
                <template v-else>
                  <div
                    class="builder-item"
                    v-for="(item, index) in buildpacksList"
                    :key="index"
                  >
                    {{ item }}
                  </div>
                </template>
              </bk-form-item>
            </template>
            <!-- Dockerfile 构建 -->
            <template v-else>
              <bk-form-item :label="`${$t('Dockerfile 路径')}：`">
                <span class="form-text">
                  {{ mirrorData.dockerfile_path || '--' }}
                </span>
              </bk-form-item>
              <!-- 暂时方式 -->
              <bk-form-item :label="`${$t('构建参数')}：`">
                <template v-if="Object.keys(mirrorData.docker_build_args).length">
                  <div
                    class="form-text"
                    v-for="(value, key) in mirrorData.docker_build_args"
                    :key="key"
                  >
                    {{ key }}={{ value }}
                  </div>
                </template>
                <template v-else>--</template>
              </bk-form-item>
            </template>
          </bk-form>
        </div>
      </div>

      <!-- 编辑态 -->
      <div
        class="content"
        v-else
      >
        <div class="form-wrapper">
          <bk-form
            ref="mirrorInfoRef"
            :model="mirrorData"
          >
            <bk-form-item :label="$t('镜像仓库')">
              <span class="form-text">
                {{ mirrorData.image_repository || '--' }}
              </span>
            </bk-form-item>
            <bk-form-item
              :label="$t('镜像 tag 规则')"
              :property="'tag_options.prefix'"
              :rules="rules.prefix"
              :icon-offset="518"
            >
              <!-- 对应正则 -->
              <bk-input
                v-model="mirrorData.tag_options.prefix"
                :placeholder="$t('自定义前缀')"
                :style="'width: 140px;'"
              ></bk-input>
              <span class="connector">+</span>
              <bk-checkbox v-model="mirrorData.tag_options.with_version">{{ $t('分支/标签') }}</bk-checkbox>
              <span class="connector">+</span>
              <bk-checkbox v-model="mirrorData.tag_options.with_build_time">{{ $t('构建时间') }}</bk-checkbox>
              <span class="connector">+</span>
              <bk-checkbox v-model="mirrorData.tag_options.with_commit_id">CommitID</bk-checkbox>
            </bk-form-item>
            <bk-form-item
              :label="$t('构建方式')"
              :property="'build_method'"
              :rules="rules.buildMethod"
            >
              <bk-radio-group v-model="mirrorData.build_method">
                <bk-radio
                  :value="item.id"
                  v-for="item in constructMethod"
                  :key="item.id"
                >
                  {{ $t(item.name) }}
                </bk-radio>
              </bk-radio-group>
            </bk-form-item>
            <bk-form-item
              :label="$t('蓝盾流水线构建')"
              :property="'use_bk_ci_pipeline'"
              v-if="curAppInfo.feature?.BK_CI_PIPELINE_BUILD"
            >
              <bk-switcher
                v-model="mirrorData.use_bk_ci_pipeline"
                theme="primary"
                size="small"
              />
              <span
                class="tips"
                @click.stop
              >
                <bk-icon type="info-circle" />
                {{ $t('支持从工蜂、Github 等平台拉取依赖，启用后需要调整代码添加凭证') }}
                <a
                  target="_blank"
                  :href="GLOBAL.DOC.BK_CI_PIPELINE_BUILD"
                >
                  {{ $t('查看使用指南') }}
                </a>
              </span>
            </bk-form-item>
            <template v-if="mirrorData.build_method === 'buildpack'">
              <bk-form-item
                :label="$t('基础镜像')"
                :property="'bp_stack_name'"
                :rules="rules.bp_stack_name"
              >
                <bk-select
                  :disabled="false"
                  v-model="mirrorData.bp_stack_name"
                  ext-cls="select-custom"
                  searchable
                >
                  <bk-option
                    v-for="option in baseImageList"
                    :key="option.image"
                    :id="option.image"
                    :name="option.name"
                  ></bk-option>
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
                <!-- 展示字段需调整 -->
                <bk-transfer
                  :source-list="sourceToolList"
                  :target-list="targetToolList"
                  :title="[$t('可选的构建工具'), $t('选中的构建工具 (按选择顺序排序)')]"
                  :display-key="'name'"
                  :setting-key="'id'"
                  :searchable="true"
                  ext-cls="build-tool-cls"
                  @change="transferChange"
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
            </template>
            <template v-else>
              <bk-form-item
                :label="$t('Dockerfile 路径')"
                :property="'dockerfile_path'"
                :rules="absolutePathRule"
                error-display-type="normal"
              >
                <bk-input
                  v-model="mirrorData.dockerfile_path"
                  :placeholder="$t('相对于构建目录的路径，若留空，默认为构建目录下名为 “Dockerfile” 的文件')"
                ></bk-input>
                <div
                  slot="tip"
                  class="examples-directory-cls"
                >
                  <!-- 示例目录 -->
                  <ExamplesDirectory
                    :root-path="sourceDir"
                    :append-path="appendPath"
                    :default-files="defaultFiles"
                    :is-dockerfile="isDockerfile"
                    :show-root="false"
                    :type="'string'"
                  />
                </div>
              </bk-form-item>

              <!-- 构建参数 -->
              <bk-form
                :model="mirrorData"
                form-type="vertical"
                ext-cls="build-params-form"
              >
                <div class="form-label">
                  {{ $t('构建参数') }}
                </div>
                <div class="form-value-wrapper">
                  <bk-button
                    v-if="!buildParams.length"
                    :text="true"
                    title="primary"
                    @click="addBuildParams"
                  >
                    <i class="paasng-icon paasng-plus-thick" />
                    {{ $t('新建构建参数') }}
                  </bk-button>
                  <template v-if="buildParams.length">
                    <div class="build-params-header">
                      <div class="name">{{ $t('参数名') }}</div>
                      <div class="value">{{ $t('参数值') }}</div>
                    </div>
                    <div
                      v-for="(item, index) in buildParams"
                      class="build-params-item"
                      :key="index"
                    >
                      <bk-form
                        :ref="`name-${index}`"
                        :model="item"
                      >
                        <bk-form-item
                          :rules="rules.buildParams"
                          :property="'name'"
                        >
                          <bk-input
                            v-model="item.name"
                            :placeholder="$t('参数名')"
                          ></bk-input>
                        </bk-form-item>
                      </bk-form>
                      <span class="equal">=</span>
                      <bk-form
                        :ref="`value-${index}`"
                        :model="item"
                      >
                        <bk-form-item
                          :rules="rules.buildParams"
                          :property="'value'"
                        >
                          <bk-input v-model="item.value"></bk-input>
                        </bk-form-item>
                      </bk-form>
                      <i
                        class="paasng-icon paasng-minus-circle-shape"
                        @click="removeBuildParams(index)"
                      ></i>
                    </div>
                  </template>
                </div>
              </bk-form>
              <bk-button
                v-if="buildParams.length"
                ext-cls="add-build-params"
                :text="true"
                title="primary"
                @click="addBuildParams"
              >
                <i class="paasng-icon paasng-plus-thick" />
                {{ $t('新建构建参数') }}
              </bk-button>
            </template>
            <bk-form-item
              :label="''"
              class="mt20"
            >
              <bk-button
                :theme="'primary'"
                class="mr10"
                :loading="switchLoading"
                @click="handleSave"
              >
                {{ $t('保存') }}
              </bk-button>
              <bk-button
                :theme="'default'"
                type="submit"
                @click="handleCancel"
                class="mr10"
              >
                {{ $t('取消') }}
              </bk-button>
            </bk-form-item>
          </bk-form>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin';
import transferDrag from '@/mixins/transfer-drag';
import { TAG_MAP } from '@/common/constants.js';
import { cloneDeep } from 'lodash';
import ExamplesDirectory from '@/components/examples-directory';

const defaultMirrorData = {
  tag_options: {
    prefix: null,
    with_version: false,
    with_build_time: false,
    with_commit_id: false,
  },
  docker_build_args: {},
  use_bk_ci_pipeline: false,
};

export default {
  mixins: [appBaseMixin, transferDrag],
  components: {
    ExamplesDirectory,
  },
  data() {
    return {
      isMirrorEdit: false,
      switchLoading: false,
      mirrorData: defaultMirrorData,
      // 构建方式
      constructMethod: [
        {
          name: '蓝鲸 Buildpack',
          id: 'buildpack',
        },
        {
          name: 'Dockerfile 构建',
          id: 'dockerfile',
        },
      ],
      methodType: {
        buildpack: '蓝鲸 Buildpack',
        dockerfile: 'Dockerfile 构建',
      },
      // 构建参数列表
      buildParams: [],
      baseImage: 2,
      // 基础镜像列表
      baseImageList: [],
      sourceToolList: [],
      targetToolList: [],
      targetToolValues: [],
      rules: {
        prefix: [
          {
            regex: /^[a-zA-Z0-9]{0,24}$/,
            message: this.$t('只能包含字母、数字，长度小于 24 个字符'),
            trigger: 'blur',
          },
        ],
        buildMethod: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
        bp_stack_name: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
        buildParams: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
      },
      absolutePathRule: [
        {
          regex: /^(?!.*(^|\/|\\|)\.{1,2}($|\/|\\|)).*$/,
          message: this.$t('不支持填写相对路径'),
          trigger: 'blur',
        },
      ],
    };
  },
  computed: {
    imageTag() {
      const tagOptions = this.mirrorData.tag_options;
      const tagStrList = [];
      for (const key in tagOptions) {
        if (tagOptions[key] && key !== 'prefix') {
          tagStrList.push(this.$t(TAG_MAP[key]));
        }
      }
      if (tagOptions.prefix) {
        tagStrList.unshift(tagOptions.prefix);
      }
      return tagStrList.join('-');
    },
    // 构建工具
    buildpacksList() {
      const buildpacks = this.mirrorData.buildpacks.map(
        (item) => `${item.display_name || item.name} (${item.description || '--'})`
      );
      return buildpacks;
    },
    baseImageText() {
      const result = this.baseImageList.find((item) => item.image === this.mirrorData.bp_stack_name);
      if (result) {
        return result.name || result.image;
      }
      return '--';
    },
    isDockerfile() {
      return this.mirrorData.build_method === 'dockerfile';
    },
    appendPath() {
      return this.mirrorData.dockerfile_path || '';
    },
    // 默认文件
    defaultFiles() {
      return [{ name: 'requirements.txt' }];
    },
    // 构建目录
    sourceDir() {
      return this.curAppModule?.repo?.source_dir || '';
    },
  },
  watch: {
    'mirrorData.bp_stack_name'(val) {
      this.setTools();
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      this.getMirrorInfo();
      this.getBaseImageList();
    },
    // 获取镜像信息
    async getMirrorInfo() {
      try {
        const results = await this.$store.dispatch('deploy/getMirrorInfo', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.$emit('set-build-method', results.build_method);
        this.mirrorData = results || defaultMirrorData;
        // 基础镜像
        if (!this.mirrorData.bp_stack_name) {
          this.mirrorData.bp_stack_name = '';
        }
        // 构建参数
        this.formatterBuildArgs();
        this.oldMirrorData = cloneDeep(this.mirrorData);
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    // 获取基础镜像信息列表（构建工具）
    async getBaseImageList() {
      try {
        const results = await this.$store.dispatch('deploy/getBaseImageList', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        results.forEach((item) => {
          item.name = `${item.slugbuilder.display_name || item.image} (${item.slugbuilder.description || '--'})`;

          item.buildpacks.forEach((item) => {
            item.name = `${item.display_name || item.name} (${item.description || '--'})`;
          });
        });
        this.baseImageList = results;
        this.setTools();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    formatterBuildArgs() {
      if (this.mirrorData.docker_build_args) {
        this.buildParams = [];
        const dockerBuild = this.mirrorData.docker_build_args;
        for (const key in dockerBuild) {
          this.buildParams.push({
            name: key,
            value: dockerBuild[key],
          });
        }
      }
    },

    // 设置当前基础镜像构建工具
    setTools() {
      // 筛选当前镜像构建工具列表
      const curTools = this.baseImageList.find((item) => item.image === this.mirrorData.bp_stack_name);
      const buildpacks = curTools?.buildpacks ? [...curTools?.buildpacks] : [];
      const result = [];
      // 兼容穿梭框右侧排序问题
      const selectedToolList = this.mirrorData?.buildpacks || [];
      // 已选择构建工具对左侧列表数据进行排序
      selectedToolList.forEach((tool) => {
        buildpacks.forEach((item, index) => {
          if (item.id === tool.id) {
            result.push(item);
            buildpacks.splice(index, 1);
          }
        });
      });
      this.sourceToolList = result.concat(buildpacks);

      // 当已选工具项
      if (selectedToolList.length) {
        this.targetToolList = selectedToolList.map((tool) => tool.id);
      }
    },

    // 保存校验
    async handleSave() {
      try {
        await this.$refs.mirrorInfoRef?.validate();
        // 构建参数校验
        const flag = await this.buildParamsValidate();
        if (flag) {
          this.saveMirrorInfo();
        }
      } catch (e) {
        console.error(e);
      }
    },

    async buildParamsValidate() {
      let flag = true;
      for (const index in this.buildParams) {
        try {
          await this.$refs[`name-${index}`][0]?.validate().finally(async () => {
            await this.$refs[`value-${index}`][0]?.validate();
          });
        } catch (error) {
          flag = false;
        }
      }
      return flag;
    },

    // 保存镜像信息
    async saveMirrorInfo() {
      this.switchLoading = true;
      const data = this.parameterConversion();

      try {
        await this.$store.dispatch('deploy/saveMirrorInfo', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('操作成功'),
        });
        await this.getMirrorInfo();
        this.handleCancel();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.switchLoading = false;
      }
    },
    parameterConversion() {
      const data = this.mirrorData;

      if (data.build_method === 'buildpack') {
        const targetToolIds = this.mixinTargetBuildpackIds || this.targetToolValues;
        // 构建工具
        data.buildpacks = targetToolIds.map((id) => this.sourceToolList.find((tool) => tool.id === id));
      } else {
        data.bp_stack_name = null;

        // 构建参数
        const dockerBuild = {};
        this.buildParams.forEach((item) => {
          dockerBuild[item.name] = item.value;
        });
        data.docker_build_args = dockerBuild;
      }

      if (data.tag_options.prefix === '') {
        data.tag_options.prefix = null;
      }

      return data;
    },
    // 新建构建参数
    addBuildParams() {
      this.buildParams.push({
        name: '',
        value: '',
      });
    },
    removeBuildParams(index) {
      this.buildParams.splice(index, 1);
    },
    handleEdit() {
      this.isMirrorEdit = true;
      this.setTools();
      this.mixinTargetBuildpackIds = null;
      this.$nextTick(() => {
        this.transferDragInit();
      });
    },
    handleCancel() {
      this.$refs.mirrorInfoRef?.clearError();
      this.isMirrorEdit = false;
      // 数据还原
      this.mirrorData = cloneDeep(this.oldMirrorData);
      this.formatterBuildArgs();
      this.setTools();
    },
    transferChange(sourceList, targetList, targetValueList) {
      this.targetToolValues = targetValueList;
      this.$nextTick(() => {
        this.transferDragInit();
      });
    },
    // 拖拽初始化
    transferDragInit() {
      const targetLiClass = '.build-tool-cls .target-list .content li';
      // 设置拖拽prop
      this.mixinSetDraggableProp(targetLiClass);
      // 目标容器拖拽
      this.mixinBindDragEvent(document.querySelector('.build-tool-cls .target-list .content'), targetLiClass);
    },
  },
};
</script>

<style lang="scss" scoped>
.mirror-main {
  position: relative;
  & > section {
    padding-bottom: 24px;
  }

  :deep(.bk-label-text) {
    color: #63656e;
  }

  :deep(.bk-form-content) {
    color: #313238;
  }

  :deep(.bk-sideslider-content) {
    background: #f5f7fa;
  }

  :deep(.bk-alert) {
    margin-bottom: 16px;
  }

  .button-edit {
    position: absolute;
    right: 0;
    top: 0;
  }
}

.mirror-main .content {
  width: 850px;
  .builder-item {
    padding: 0 10px;
    line-height: 32px;
    position: relative;

    &:before {
      content: '';
      font-size: 12px;
      position: absolute;
      left: 0;
      top: 15px;
      width: 3px;
      height: 3px;
      display: inline-block;
      background: #656565;
    }
  }
}

.mirror-info {
  :deep(.bk-form-item + .bk-form-item) {
    margin-top: 10px;
  }
}

.build-title {
  position: relative;
  font-weight: 700;
  font-size: 14px;
  color: #313238;

  &.edit::after {
    content: '*';
    height: 8px;
    line-height: 1;
    color: #ea3636;
    font-size: 12px;
    position: absolute;
    display: inline-block;
    vertical-align: middle;
    top: 50%;
    transform: translate(3px, -50%);
  }
}

.mirror-info {
  h4 {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
    padding: 0;
  }

  .form-wrapper {
    .connector {
      margin: 0 8px;
      color: #63656e;
    }
  }

  .build-params-header {
    display: flex;
    line-height: 32px;
    .name,
    .value {
      flex: 1;
    }
    .value {
      margin-right: -5px;
    }
  }

  .build-params-item {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
    width: 100%;

    &:last-child {
      margin-bottom: 0;
    }

    .equal {
      font-weight: 700;
      font-size: 14px;
      color: #ff9c01;
      margin: 0 11px;
    }

    i {
      margin-left: 12px;
      color: #ea3636;
      cursor: pointer;
    }
  }

  .add-build-params {
    margin-left: 150px;
  }

  .build-params-form {
    margin-top: 10px;
    margin-bottom: 16px;
    display: flex;

    .form-label {
      width: 150px;
      line-height: 32px;
      padding-right: 24px;
      text-align: right;
    }

    .form-value-wrapper {
      line-height: 32px;
      width: 100%;
      flex: 1;

      .bk-form {
        flex: 1;
      }

      .bk-form-item {
        margin-top: 0 !important;
      }
    }
  }
}

.tips {
  margin-left: 12px;
  font-size: 12px;
  color: #979ba5;
  i {
    font-size: 14px !important;
  }
}

/* 穿梭框 */
:deep(.build-tool-cls) {
  .content {
    padding-bottom: 42px;
  }

  /* 穿梭框样式设置 */
  .transfer-source-item {
    white-space: nowrap;
    text-overflow: ellipsis;
    overflow: hidden;
  }

  .target-list .content li.moving {
    background: transparent;
    color: transparent;
    border: 1px dashed #ccc;
  }
}
.left-header label,
.right-header label {
  display: inline-block;
  font-size: 12px;
}
.add-all {
  display: inline-block;
  float: right;
  cursor: pointer;
  font-size: 14px;
  span {
    color: #3a84ff;
    &.disabled {
      cursor: not-allowed;
      opacity: 0.5;
    }
  }
}
.add-all {
  display: inline-block;
  float: right;
  cursor: pointer;
  font-size: 12px;
}
.add-all span {
  color: #3a84ff;
}
.disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.remove-all {
  display: inline-block;
  float: right;
  cursor: pointer;
  font-size: 12px;
}
.remove-all span {
  color: #ea3636;
}
.empty-content {
  position: relative;
  top: 120px;
  text-align: center;
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
