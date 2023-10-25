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
          <bk-table-column :label="$t('挂载目录')" prop="mount_path"></bk-table-column>
          <bk-table-column
            :label="$t('生效环境')"
            :filters="envSelectList"
            :filter-method="sourceFilterMethod"
            :filter-multiple="false"
            prop="environment_name"
          >
            <template slot-scope="{ row }">
              <div>{{ $t(envEnums[row.environment_name]) || $t('所有环境') }}</div>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('文件内容')" width="410" prop="source_config_data">
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
    <bk-sideslider
      :is-show.sync="volumeDefaultSettings.isShow"
      :quick-close="true"
      :width="960"
      ext-cls="volume-slider"
    >
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
              ext-cls="volume-file-content"
            >
              <div class="addFile">
                <div class="addFileText" v-if="!isAddFile" @click="addFile">
                  <i class="icon paasng-icon paasng-plus-circle-shape" />&emsp;{{ $t('添加文件') }}
                </div>
                <div class="addFileInput" v-else>
                  <bk-input
                    :placeholder="$t('请输入')"
                    v-model="addFileInput"
                    :right-icon="'icon paasng-icon paasng-correct'"
                    @right-icon-click="handlerAddConfirm"
                  ></bk-input>
                </div>
              </div>
              <bk-tab
                class="tab-container"
                tab-position="right"
                label-width="400"
                :active.sync="active"
                @tab-change="tabChange"
              >
                <bk-tab-panel
                  v-for="(panel, index) in volumeFormData.source_config_data"
                  :label="panel.label"
                  :name="panel.name"
                  :key="`${panel.name}and${index}`"
                >
                  <template slot="label">
                    <div
                      :ref="`labelContainer${panel.label}`"
                      class="label-container"
                      @mouseenter="handleEnter(panel.label)"
                      @mouseleave="handleLeave(panel.label)"
                    >
                      <div class="label-text">
                        {{ panel.label }}
                      </div>
                      <div class="label-icon" :ref="`labelIcon${panel.label}`">
                        <i class="paasng-icon paasng-edit2" @click="fileEdit(panel.label)" />&nbsp;
                        <i class="icon paasng-icon paasng-icon-close" @click="fileDelete(panel.label)" />
                      </div>
                    </div>
                    <div class="editInput" :ref="`editInput${panel.label}`">
                      <bk-input
                        v-model="panel.label"
                        :right-icon="'icon paasng-icon paasng-correct'"
                        @right-icon-click="handlerEditConfirm(panel.label, index)"
                      >
                      </bk-input>
                    </div>
                  </template>
                </bk-tab-panel>
              </bk-tab>
              <div class="editor">
                <resource-editor
                  ref="editorRefSlider"
                  key="editor"
                  v-model="sliderEditordetail"
                  v-bkloading="{ isDiaLoading, opacity: 1, color: '#1a1a1a' }"
                  :height="fullScreen ? clientHeight : fileSliderConfig.height"
                  @error="handleEditorErr"
                />
                <EditorStatus v-show="!!editorErr.message" class="status-wrapper" :message="editorErr.message" />
              </div>
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
      sliderEditordetail: '',
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
        height: 350,
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
      curTabDom: null,
    };
  },
  computed: {
    formatConfigData() {
      return function (tags) {
        const containerWidth = 410;
        const tagWidth = 90;
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
        const containerWidth = 410;
        const tagWidth = 90;
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
    this.init();
  },
  methods: {
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
      this.isAddFile = false;
      this.active = '';
      this.volumeFormData = {
        name: '',
        mount_path: '',
        environment_name: 'stag',
        source_config_data: [],
        source_type: 'ConfigMap',
      };
      this.volumeDefaultSettings.isShow = true;
      this.$nextTick(() => {
        this.$refs.editorRefSlider.setValue('');
      });
    },
    // 获取挂载卷list
    getVolumeList() {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/mres/volume_mounts/`;
      this.$http
        .get(url)
        .then((res) => {
          this.volumeList = res.results;
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
      _row.source_config_data = Object.entries(_row.source_config_data).map(([key, value]) => ({
        name: key,
        label: key,
        content: value,
      }));
      this.volumeFormData = _row;
      this.volumeDefaultSettings.isShow = true;
      this.active = this.volumeFormData.source_config_data[0].label;
      const editContent = this.convertToObjectIfPossible(this.volumeFormData.source_config_data[0].content);
      this.$nextTick(() => {
        this.$refs.editorRefSlider.setValue(editContent);
      });
    },
    // 删除挂载券
    deleteVolume(row) {
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/mres/volume_mounts/${row.id}`;
      this.$http
        .delete(url)
        .then(() => {
          this.$paasMessage({
            theme: 'success',
            message: this.$t('删除成功'),
          });
        })
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
      this.detail = row[item];
      // eslint-disable-next-line no-underscore-dangle
      const _detail = cloneDeep(this.detail);
      const resultFormatDetail = this.convertToObjectIfPossible(_detail);
      this.$refs.editorRefDialog?.setValue(resultFormatDetail);
    },
    // 筛选生效环境
    sourceFilterMethod(value, row, column) {
      const { property } = column;
      return row[property] === value;
    },
    // 确定新增或编辑挂载券
    confirmVolume() {
      // eslint-disable-next-line no-underscore-dangle
      const _row = cloneDeep(this.volumeFormData);
      const testConfigData = _row.source_config_data;
      const formatConfig = testConfigData.reduce((obj, item) => {
        // eslint-disable-next-line no-param-reassign
        obj[item.label] = item.content;
        return obj;
      }, {});
      _row.source_config_data = formatConfig;
      console.log(_row);
      if (this.curType === 'add') {
        const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/mres/volume_mounts/`;
        this.$http
          .post(url, _row)
          .then(() => {
            this.$paasMessage({
              theme: 'success',
              message: this.$t('创建成功'),
            });
            this.volumeDefaultSettings.isShow = false;
            this.curType = '';
            this.getVolumeList();
          })
          .catch((err) => {
            this.$paasMessage({
              theme: 'error',
              message: err.message || err.detail || this.$t('创建失败'),
            });
          });
      } else if (this.curType === 'edit') {
        const curVolumId = this.volumeFormData.id;
        const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/mres/volume_mounts/${curVolumId}`;
        this.$http
          .put(url, _row)
          .then(() => {
            this.$paasMessage({
              theme: 'success',
              message: this.$t('修改成功'),
            });
            this.volumeDefaultSettings.isShow = false;
            this.curType = '';
            this.getVolumeList();
            console.log(this.volumeFormData);
          })
          .catch(() => {
            this.$paasMessage({
              theme: 'error',
              message: this.$t('修改失败'),
            });
          });
      }
    },
    // 取消新增或编辑挂载券
    cancelVolume() {
      this.volumeDefaultSettings.isShow = false;
      this.curType = '';
    },
    // tab切换
    tabChange(val) {
      if (val === '') {
        this.$refs.editorRefSlider.setValue('');
        return;
      }
      const curTab = this.volumeFormData.source_config_data.find(item => item.name === val);
      if (curTab === undefined) {
        this.active = this.volumeFormData.source_config_data[0].label;
        const curContent = this.convertToObjectIfPossible(this.volumeFormData.source_config_data[0].content);
        this.$refs.editorRefSlider.setValue(curContent);
        return;
      }
      // eslint-disable-next-line no-underscore-dangle
      const _detail = cloneDeep(curTab.content);
      this.active = val;
      this.isAddFile = false;
      const resultFormatDetail = this.convertToObjectIfPossible(_detail);
      this.$refs.editorRefSlider.setValue(resultFormatDetail);
      this.volumeFormData.source_config_data.forEach((item) => {
        this.$refs[`editInput${item.label}`][0].style.display = 'none';
        this.$refs[`labelContainer${item.label}`][0].style.display = 'flex';
      });
    },
    // 转换数据格式
    convertToObjectIfPossible(value) {
      try {
        const formatDetail = value.replace(/'/g, '"');
        const parsedValue = JSON.parse(formatDetail);
        if (typeof parsedValue === 'object' && parsedValue !== null) {
          return parsedValue;
        }
      } catch (error) {
        // 解析失败，保持原样
      }
      return value;
    },
    // 鼠标进入tab
    handleEnter(label) {
      this.$refs[`labelIcon${label}`][0].style.display = 'block';
    },
    // 鼠标离开tab
    handleLeave(label) {
      this.$refs[`labelIcon${label}`][0].style.display = 'none';
    },
    // 添加文件
    addFile() {
      this.isAddFile = true;
      this.$refs.editorRefSlider?.setValue('');
      this.addFileInput = '';
      this.volumeFormData.source_config_data.forEach((item) => {
        this.$refs[`editInput${item.label}`][0].style.display = 'none';
        this.$refs[`labelContainer${item.label}`][0].style.display = 'flex';
      });
      const ulDom = document.querySelector('.tab-container .bk-tab-label-list ');
      const tabActiveDom = document.querySelector('.tab-container .active');
      if (!tabActiveDom) {
        return;
      }
      this.curTabDom = tabActiveDom;
      tabActiveDom.classList.remove('active');
      ulDom.classList.remove('bk-tab-label-list-has-bar');
    },
    handleBlurAddInput() {
      if (this.addFileInput.trim() === '') {
        this.isAddFile = false;
        if (this.volumeFormData.source_config_data.length === 0) {
          return;
        }
        console.log(this.volumeFormData);
        const curTab = this.volumeFormData.source_config_data.find(item => item.name === this.active);
        const curContent = this.convertToObjectIfPossible(curTab.content);
        this.$refs.editorRefSlider.setValue(curContent);
        return;
      }
      const fileName = this.volumeFormData.source_config_data;
      const flag = fileName.some(item => item.label === this.addFileInput);
      if (flag) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('文件同名，请重新编辑'),
        });
        return;
      }
      if (this.$refs.editorRefSlider?.getValue() === '') {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('文件内容不能为空'),
        });
        return;
      }
      this.active = this.addFileInput;
      const isObj = JSON.stringify(this.sliderEditordetail) === '{}';
      const curContent = this.$refs.editorRefSlider?.getValue();
      const content = isObj ? curContent : JSON.stringify(this.sliderEditordetail);
      const addFileContent = {
        name: this.addFileInput,
        label: this.addFileInput,
        content,
      };
      this.isAddFile = false;
      this.volumeFormData.source_config_data.unshift(addFileContent);
    },
    // 添加确认
    handlerAddConfirm() {
      const ulDom = document.querySelector('.tab-container .bk-tab-label-list ');
      if (this.curTabDom) {
        ulDom.classList.add('bk-tab-label-list-has-bar');
        this.curTabDom.classList.add('active');
      }
      this.handleBlurAddInput();
    },
    // 编辑文件内容的tab
    fileEdit(label) {
      this.isAddFile = false;
      const curTab = this.volumeFormData.source_config_data.find(item => item.label === label);
      const curContent = this.convertToObjectIfPossible(curTab.content);
      this.$refs.editorRefSlider.setValue(curContent);
      this.$refs[`editInput${label}`][0].style.display = 'block';
      this.$refs[`labelContainer${label}`][0].style.display = 'none';
      const hideTab = this.volumeFormData.source_config_data.filter(item => item.label !== label);
      hideTab.forEach((item) => {
        this.$refs[`editInput${item.label}`][0].style.display = 'none';
        this.$refs[`labelContainer${item.label}`][0].style.display = 'flex';
      });
      console.log(hideTab);
    },
    handleBlurEditInput(label, index) {
      this.$nextTick(() => {
        console.log(this.$refs);
        Object.keys(this.$refs).forEach((item) => {
          if (Array.isArray(this.$refs[item]) && this.$refs[item].length === 0) {
            // 检查引用是否为空
            delete this.$refs[item]; // 删除引用
          }
        });
      });
      if (label.trim() === '') {
        return;
      }
      const volumeData = this.volumeFormData.source_config_data;
      const fileName = cloneDeep(volumeData);
      const curTab = volumeData.find(item => item.label === label);
      this.active = curTab.name;
      const isObj = JSON.stringify(this.sliderEditordetail) === '{}';
      const curContent = this.$refs.editorRefSlider?.getValue();
      curTab.content = isObj ? curContent : JSON.stringify(this.sliderEditordetail);
      fileName.splice(index, 1);
      const flag = fileName.some(item => item.label === label);
      if (flag) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('文件同名，请重新编辑'),
        });
        return;
      }
      this.$refs[`editInput${label}`][0].style.display = 'none';
      this.$refs[`labelContainer${label}`][0].style.display = 'flex';
    },
    // 编辑确认
    handlerEditConfirm(label, index) {
      this.handleBlurEditInput(label, index);
    },
    // 删除文件内容的tab
    fileDelete(label) {
      this.isAddFile = false;
      this.active = this.volumeFormData.source_config_data[0].label;
      const curContent = this.convertToObjectIfPossible(this.volumeFormData.source_config_data[0].content);
      this.$refs.editorRefSlider.setValue(curContent);
      const volumeFile = this.volumeFormData.source_config_data;
      const curConfigData = volumeFile.filter(item => item.label !== label);
      this.volumeFormData.source_config_data = curConfigData;
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
.volume-slider {
  .bk-sideslider-wrapper {
    .bk-sideslider-content {
      height: calc(100vh - 129px);
    }
  }
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
      .slider-volume-content {
        padding: 20px 40px;
        .name-tip {
          color: #979ba5;
        }
        .bk-form-content {
          position: relative;
          background-color: #f5f7fa;
          .addFile {
            background-color: #f5f7fa;
            color: #3a84ff;
            width: 200px;
            height: 50px;
            line-height: 50px;
            padding: 0 12px;
            cursor: pointer;
            .addFileInput {
              /deep/ .paasng-correct {
                font-size: 24px;
              }
            }
          }
          .tab-container {
            background-color: #f5f7fa;
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
                          cursor: pointer;
                          font-size: 20px;
                        }
                      }
                    }
                    .editInput {
                      display: none;
                      .paasng-correct {
                        font-size: 24px;
                      }
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
          .editor {
            width: 663px;
            position: absolute;
            top: 0px;
            left: 200px;
          }
        }
      }
    }
  }
}
</style>
