<template>
  <div class="volume-container">
    <paas-content-loader
      :is-loading="isLoading"
      placeholder="deploy-volume-loading"
      :is-transition="false"
      :offset-top="0"
      :offset-left="0"
      class="middle"
    >
      <section v-show="!isLoading">
        <bk-alert type="info" closable>
          <span slot="title">
            {{ $t('可以通过挂载文件的方式，向容器中注入配置信息。') }}
          </span>
        </bk-alert>
        <bk-button theme="primary" class="mb15 mt20" @click="handleCreate('add')">
          <i class="paasng-icon paasng-plus mr5" /> {{ $t('新增挂载') }}
        </bk-button>
        <bk-table :data="volumeList" size="small" :outer-border="false" :header-border="false">
          <bk-table-column :label="$t('名称')" prop="name"></bk-table-column>
          <bk-table-column label="挂载目录" prop="mount_path"></bk-table-column>
          <bk-table-column
            :label="$t('生效环境')"
            :filters="envSelectList"
            :filter-method="sourceFilterMethod"
            :filter-multiple="false"
            prop="environment_name"
          >
            <template slot-scope="{ row }">
              <div>{{ envEnums[row.environment_name] || $t('所有环境') }}</div>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('文件内容')" width="470" prop="source_config_data">
            <template slot-scope="{ row, $index }">
              <div class="tag-container">
                <bk-tag
                  v-for="item in visibleTags(row.source_config_data)"
                  :key="item"
                  class="activeTag"
                  @click="handleTag(row.source_config_data, item)"
                >
                  {{ item }}
                </bk-tag>
                <div
                  id="tooltipContent"
                  v-if="Object.keys(row.source_config_data).length !== visibleTags(row.source_config_data).length"
                >
                  <bk-tag
                    class="activeTag"
                    v-for="item in formatConfigData(row.source_config_data)"
                    :key="item"
                    @click="handleTag(row.source_config_data, item)"
                  >
                    {{ item }}
                  </bk-tag>
                </div>
                <a
                  :ref="`tooltipContent${$index}`"
                  class="plusIcon"
                  v-bk-tooltips="tagTipConfig"
                  v-if="Object.keys(row.source_config_data).length !== visibleTags(row.source_config_data).length"
                >
                  <bk-tag :key="'more'">
                    +{{ Object.keys(row.source_config_data).length - visibleTags(row.source_config_data).length }}
                  </bk-tag>
                </a>
              </div>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('操作')">
            <template slot-scope="props">
              <bk-button class="mr10" theme="primary" text @click="editVolume('edit', props.row)">
                {{ $t('编辑') }}
              </bk-button>
              <bk-button class="mr10" theme="primary" text @click="deleteVolume(props.row)">
                {{ $t('删除') }}</bk-button
              >
            </template>
          </bk-table-column>
        </bk-table>
      </section>
    </paas-content-loader>
    <!-- 文件内容详情 -->
    <bk-dialog
      v-model="fileDialogConfig.visiable"
      :width="fileDialogConfig.dialogWidth"
      theme="primary"
      :mask-close="false"
      header-position="left"
      :title="$t('文件内容详情')"
      :show-footer="false"
    >
      <resource-editor
        ref="editorRefDialog"
        key="editor"
        v-model="detail"
        v-bkloading="{ isDiaLoading, opacity: 1, color: '#1a1a1a' }"
        :height="fullScreen ? clientHeight : fileDialogConfig.height"
        @error="handleEditorErr"
      />
      <EditorStatus v-show="!!editorErr.message" class="status-wrapper" :message="editorErr.message" />
    </bk-dialog>
    <!-- 新增/编辑挂卷 -->
    <bk-sideslider :is-show.sync="volumeDefaultSettings.isShow" :quick-close="true" :width="960">
      <div slot="header">
        {{ $t('新增/编辑挂载券') }}&emsp;
        <span style="color: #979ba5; font-size: 14px" v-if="curType === 'edit'">{{ volumeFormData.name }}</span>
      </div>
      <div slot="content">
        <div class="slider-volume-content">
          <bk-form :label-width="200" form-type="vertical" :model="volumeFormData">
            <bk-form-item
              :label="$t('名称')"
              :required="true"
              style="width: 560px"
              :property="'name'"
              :rules="rules.name"
            >
              <bk-input
                v-model="volumeFormData.name"
                :placeholder="$t('请输入 2-30 字符的小写字母、数字、连字符(-)，以小写字母开头')"
              ></bk-input>
              <p class="mt5 mb0 f12 name-tip" slot="tip">{{ $t('唯一标识，创建后不可修改') }}</p>
            </bk-form-item>
            <bk-form-item
              :label="$t('挂载目录')"
              :required="true"
              style="width: 560px; margin-top: 15px"
              :property="'mount_path'"
              :rules="rules.mount_path"
            >
              <bk-input v-model="volumeFormData.mount_path" :placeholder="$t('请输入')"></bk-input>
            </bk-form-item>
            <bk-form-item
              :label="$t('生效环境')"
              :required="true"
              style="margin-top: 27px"
              :property="'environment_name'"
            >
              <bk-radio-group v-model="volumeFormData.environment_name">
                <bk-radio :value="'stag'">{{ $t('仅预发布环境') }} </bk-radio>
                <bk-radio :value="'prod'">{{ $t('仅生产环境') }} </bk-radio>
                <bk-radio :value="'_global_'">{{ $t('所有环境') }} </bk-radio>
              </bk-radio-group>
            </bk-form-item>
            <bk-form-item
              :label="$t('文件内容')"
              :required="true"
              style="margin-top: 15px"
              :property="'source_config_data'"
            >
              <div class="addFile" @click="addFile">
                <div class="addFileText" v-if="!isAddFile">
                  <i class="icon paasng-icon paasng-plus-circle-shape" />&emsp;{{ $t('添加文件') }}
                </div>
                <div class="addFileInput" v-else>
                  <bk-input :placeholder="$t('请输入')" v-model="addFileInput" @blur="handleBlurAddInput"></bk-input>
                </div>
              </div>
              <bk-tab class="tab-container" tab-position="right" label-width="400" :active.sync="active">
                <bk-tab-panel
                  v-for="(panel, index) in volumeFormData.source_config_data"
                  :name="panel.name"
                  :label="panel.label"
                  :key="panel.name"
                >
                  <template slot="label">
                    <div
                      :ref="`labelContainer${index}`"
                      class="label-container"
                      @mouseenter="handleEnter(index)"
                      @mouseleave="handleLeave(index)"
                    >
                      <div class="label-text">
                        {{ panel.label }}
                      </div>
                      <div class="label-icon" :ref="`labelIcon${index}`">
                        <i class="paasng-icon paasng-edit2" @click="fileEdit(index)" />&nbsp;
                        <i class="icon paasng-icon paasng-icon-close" />
                      </div>
                    </div>
                    <div class="editInput" :ref="`editInput${index}`">
                      <bk-input v-model="panel.label" @blur="handleBlurEditInput(panel.label, index)"> </bk-input>
                    </div>
                  </template>
                  <div class="tab-content">
                    <resource-editor
                      ref="editorRef"
                      key="editor"
                      v-model="panel.content"
                      v-bkloading="{ isDiaLoading, opacity: 1, color: '#1a1a1a' }"
                      :height="fullScreen ? clientHeight : fileSliderConfig.height"
                      @error="handleEditorErr"
                    />
                    <EditorStatus v-show="!!editorErr.message" class="status-wrapper" :message="editorErr.message" />
                  </div>
                </bk-tab-panel>
              </bk-tab>
            </bk-form-item>
          </bk-form>
        </div>
      </div>
      <div slot="footer">
        <bk-button style="margin-left: 30px" theme="primary" @click="confirmVolume()">{{ $t('确定') }} </bk-button>
        <bk-button theme="default" @click="cancelVolume()">{{ $t('取消') }}</bk-button>
      </div>
    </bk-sideslider>
  </div>
</template>

<script>
import { cloneDeep } from 'lodash';
import appBaseMixin from '@/mixins/app-base-mixin';
import ResourceEditor from './comps/deploy-resource-editor';
import EditorStatus from './comps/deploy-resource-editor/editor-status';
// import i18n from '@/language/i18n.js';
import { ENV_ENUM } from '@/common/constants';

export default {
  components: {
    ResourceEditor,
    EditorStatus,
  },
  mixins: [appBaseMixin],
  props: {},
  data() {
    return {
      isEdit: false,
      detail: {},
      isDiaLoading: false,
      isLoading: true,
      fullScreen: false,
      clientHeight: document.body.clientHeight,
      editorErr: {
        type: '',
        message: '',
      },
      // 编辑器上面
      addFileInput: '',
      isAddFile: false,
      curType: '',
      volumeList: [],
      fileDialogConfig: {
        visiable: false,
        content: '',
        dialogWidth: 640,
        height: 360,
      },
      fileSliderConfig: {
        content: '',
        dialogWidth: 660,
        height: 400,
      },
      tagTipConfig: {
        allowHTML: true,
        theme: 'light',
        content: '#tooltipContent',
      },
      volumeDefaultSettings: {
        isShow: false,
      },
      rules: {
        name: [
          {
            required: true,
            message: this.$t('该字段不能为空'),
            trigger: 'blur',
          },
          {
            regex: /^[a-z][a-z0-9-]{1,29}$/,
            message: this.$t('请输入 2-30 字符的小写字母、数字、连字符(-)，以小写字母开头'),
            trigger: 'blur',
          },
        ],
        mount_path: [
          {
            required: true,
            message: this.$t('该字段不能为空'),
            trigger: 'blur',
          },
          {
            regex: /^\/.*\/$/,
            message: this.$t('目录格式不对'),
            trigger: 'blur',
          },
          {
            validator: () => {
              const flag = this.volumeList.some(item => item.mount_path === this.volumeFormData.mount_path
                  && item.environment_name === this.volumeFormData.environment_name);
              console.log(flag);
              if (flag) {
                return false;
              }
              return true;
            },
            message: () => this.$t('同环境和路径挂载卷已存在'),
            trigger: 'blur change',
          },
        ],
        environment_name: [
          {
            required: true,
            trigger: 'change',
          },
        ],
        source_config_data: [],
      },
      volumeFormData: {
        name: '',
        mount_path: '',
        environment_name: 'stag',
        source_config_data: [],
        source_type: 'ConfigMap',
      },
      active: '',
      currentPosition: 'left',
      editTabIndex: 9,
      envSelectList: [
        { value: '_global_', text: this.$t('所有环境') },
        { value: 'stag', text: this.$t('仅预发布环境') },
        { value: 'prod', text: this.$t('仅生产环境') },
      ],
      envEnums: ENV_ENUM,
    };
  },
  computed: {
    formatConfigData() {
      return function (tags) {
        const containerWidth = 420;
        const tagWidth = 92;
        const maxVisibleCount = Math.floor(containerWidth / tagWidth);
        const curTags = Object.keys(tags);
        if (curTags.length <= maxVisibleCount) {
          return curTags;
        }
        const dataLength = curTags.slice(0, maxVisibleCount).length;
        return curTags.slice(dataLength);
      };
    },
    visibleTags() {
      return function (tags) {
        const containerWidth = 420;
        const tagWidth = 92;
        const maxVisibleCount = Math.floor(containerWidth / tagWidth);
        const curTags = Object.keys(tags);
        if (curTags.length <= maxVisibleCount) {
          return curTags;
        }
        return curTags.slice(0, maxVisibleCount);
      };
    },
  },
  watch: {},
  mounted() {
    this.getVolumeList();
  },
  created() {
    this.init();
  },
  methods: {
    test() {
      this.isEdit = true;
    },
    handleEditorErr(err) {
      // 捕获编辑器错误提示
      this.editorErr.type = 'content'; // 编辑内容错误
      this.editorErr.message = err;
    },
    init() {
      this.isLoading = true;
      this.getVolumeList();
    },
    // 新增挂载
    handleCreate(type) {
      this.curType = type;
      this.volumeFormData = {
        name: '',
        mount_path: '',
        environment_name: 'stag',
        source_config_data: [],
        source_type: 'ConfigMap',
      };
      this.volumeDefaultSettings.isShow = true;
    },
    // 获取挂载卷list
    getVolumeList() {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/mres/volume_mounts/`;
      this.$http
        .get(url)
        .then((res) => {
          this.volumeList = res.results;
          console.log(this.volumeList);
        })
        .finally(() => {
          this.isLoading = false;
        });
    },
    // 编辑挂载券
    editVolume(type, row) {
      this.isAddFile = false;
      this.curType = type;
      // eslint-disable-next-line no-underscore-dangle
      const _row = cloneDeep(row);
      const formatConfigData = Object.entries(_row.source_config_data).map(([key, value]) => ({
        name: key,
        label: key,
        content: value,
      }));
      console.log(formatConfigData);
      this.volumeFormData = _row;
      this.volumeFormData.source_config_data = formatConfigData;
      this.volumeDefaultSettings.isShow = true;
      console.log(this.volumeFormData);
    },
    // 删除挂载券
    deleteVolume(row) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/mres/volume_mounts/${row.id}`;
      this.$http
        .delete(url)
        .then(() => {})
        .catch((err) => {
          this.$paasMessage({
            theme: 'error',
            message: err.message || err.detail || this.$t('删除失败，请重新操作'),
          });
        })
        .finally(() => {
          this.getVolumeList();
        });
    },
    // 点击标签
    handleTag(row, item) {
      this.fileDialogConfig.visiable = true;
      const addressDom = document.querySelectorAll('.plusIcon');
      for (const item of addressDom) {
        // eslint-disable-next-line no-underscore-dangle
        if (item._tippy) {
          // eslint-disable-next-line no-underscore-dangle
          item._tippy.hide();
        }
      }
      this.detail = { [item]: row[item] };
      this.$refs.editorRefDialog?.setValue(this.detail);
    },
    // 筛选生效环境
    sourceFilterMethod(value, row, column) {
      const { property } = column;
      return row[property] === value;
    },
    // 确定新增或编辑挂载券
    confirmVolume() {
      const testConfigData = cloneDeep(this.volumeFormData.source_config_data);
      const formatConfig = testConfigData.reduce((obj, item) => {
        // eslint-disable-next-line no-param-reassign
        obj[item.label] = item.content;
        return obj;
      }, {});
      this.volumeFormData.source_config_data = formatConfig;
      if (this.curType === 'add') {
        const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/mres/volume_mounts/`;
        this.$http
          .post(url, this.volumeFormData)
          .then(() => {
            this.$paasMessage({
              theme: 'success',
              message: this.$t('创建成功'),
            });
          })
          .catch((err) => {
            this.$paasMessage({
              theme: 'error',
              message: err.message || err.detail || this.$t('创建失败'),
            });
          })
          .finally(() => {
            this.curType = '';
            this.getVolumeList();
          });
      } else if (this.curType === 'edit') {
        const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/mres/volume_mounts/`;
        this.$http
          .put(url)
          .then(() => {
            this.$paasMessage({
              theme: 'success',
              message: this.$t('创建成功'),
            });
          })
          .catch(() => {
            this.$paasMessage({
              theme: 'error',
              message: this.$t('创建失败'),
            });
          })
          .finally(() => {
            this.curType = '';
            this.getVolumeList();
          });
      }
      this.volumeDefaultSettings.isShow = false;
    },
    // 取消新增或编辑挂载券
    cancelVolume() {
      this.volumeDefaultSettings.isShow = false;
      this.curType = '';
    },
    // 鼠标进入tab
    handleEnter(index) {
      this.$refs[`labelIcon${index}`][0].style.display = 'block';
    },
    // 鼠标离开tab
    handleLeave(index) {
      this.$refs[`labelIcon${index}`][0].style.display = 'none';
    },
    // 添加文件
    addFile() {
      this.addFileInput = '';
      this.isAddFile = true;
    },
    // 添加文件input失焦
    handleBlurAddInput() {
      if (this.addFileInput.trim() === '') {
        this.isAddFile = false;
        return;
      }
      const flag = this.volumeFormData.source_config_data.some(item => item.label === this.addFileInput);
      if (flag) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('文件同名！'),
        });
        return;
      }
      this.volumeFormData.source_config_data.push({
        name: this.addFileInput,
        label: this.addFileInput,
        content: '',
      });
      this.isAddFile = false;
      console.log(this.addFileInput);
      console.log(this.volumeFormData);
      console.log(this.$refs);
    },
    // 编辑文件内容的tab
    fileEdit(index) {
      this.$refs[`editInput${index}`][0].style.display = 'block';
      this.$refs[`labelContainer${index}`][0].style.display = 'none';
    },
    // 编辑文件input失焦
    handleBlurEditInput(label, index) {
      if (label.trim() === '') {
        return;
      }
      this.$refs[`editInput${index}`][0].style.display = 'none';
      this.$refs[`labelContainer${index}`][0].style.display = 'flex';
      console.log(this.volumeFormData);
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
.volume-container {
  padding: 0 20px 20px;
  min-height: 200px;
}
.activeTag:hover {
  color: #3a84ff;
}
.bk-sideslider {
  .bk-sideslider-wrapper {
    .bk-sideslider-content {
      max-height: calc(100vh - 129px) !important;

      .slider-volume-content {
        padding: 20px 40px;
        .name-tip {
          color: #979ba5;
        }
        .addFile {
          background-color: #f5f7fa;
          color: #3a84ff;
          width: 200px;
          height: 50px;
          line-height: 50px;
          padding: 0 12px;
          cursor: pointer;
        }
        .tab-container {
          min-height: 300px !important;
          /deep/ .bk-tab-header {
            order: 1;
            background-color: #f5f7fa;
            padding: 0;
            .bk-tab-label-wrapper {
              .bk-tab-label-item {
                width: 200px;
                border: none;
                .bk-tab-label {
                  width: 100%;
                  .label-container {
                    width: 100%;
                    display: flex;
                    justify-content: space-between;
                    .label-icon {
                      display: none;
                      .paasng-edit2 {
                        cursor: pointer;
                      }
                      .paasng-icon-close {
                        font-size: 20px;
                      }
                    }
                  }
                  .editInput {
                    display: none;
                  }
                }
              }
              .active {
                background-color: #fff;
              }
            }
            .bk-tab-label-wrapper::after {
              border: none;
            }
          }
          /deep/ .bk-tab-section {
            padding: 0;
          }
          /deep/ .bk-tab-header::before {
            height: 0;
          }
          /deep/ .bk-tab-header::after {
            height: 0;
          }
        }
      }
    }
  }
}
</style>
