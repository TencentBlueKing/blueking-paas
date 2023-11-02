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
        <bk-button theme="primary" class="mb15 mt20" @click="handleCreate">
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
              <bk-button class="mr10" theme="primary" text @click="handleEditVolume(props.row)">
                {{ $t('编辑') }}
              </bk-button>
              <bk-button class="mr10" theme="primary" text @click="handleDelete(props.row)">
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
      header-position="left"
      :title="$t('文件内容详情')"
      :show-footer="false"
    >
      <resource-editor
        ref="resourceEditorRef"
        key="editor"
        v-model="detail"
        v-bkloading="{ isDiaLoading, opacity: 1, color: '#1a1a1a' }"
        :height="fullScreen ? clientHeight : fileDialogConfig.height"
      />
    </bk-dialog>
    <!-- 新增/编辑挂卷 -->
    <bk-sideslider
      :is-show.sync="volumeDefaultSettings.isShow"
      :quick-close="true"
      :width="960"
      ext-cls="volume-slider"
    >
      <div slot="header">
        {{volumeFormData.id ? $t('编辑') : $t('新增')}}{{ $t('挂载卷') }}
        <span class="header-sub-name pl5">
          {{ volumeFormData.name }}
        </span>
      </div>
      <div slot="content">
        <div class="slider-volume-content">
          <bk-form :label-width="200" form-type="vertical" :model="volumeFormData" ref="formRef">
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
              <bk-input
                v-model="volumeFormData.mount_path"
                :placeholder="$t('请输入以斜杆(/)开头，且不包含空字符串的路径')"
              ></bk-input>
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
              <div class="file-container flex-row">
                <div class="label-container">
                  <div class="addFile">
                    <div class="addFileText" v-if="!isAddFile" @click="handleAddFile">
                      <i class="icon paasng-icon paasng-plus-circle-shape pr10" />{{ $t('添加文件') }}
                    </div>
                    <div class="addFileInput" v-else>
                      <bk-input
                        ref="addFileInputRef"
                        :placeholder="$t('请输入')"
                        v-model="addFileInput"
                        @blur="handlerAddConfirm"
                        @enter="handleEnter('add')"
                      ></bk-input>
                    </div>
                  </div>
                  <div
                    class="label-container flex-row justify-content-between"
                    v-for="(item, index) in volumeFormData.sourceConfigArrData"
                    :key="index"
                    @mouseenter="hoverKey = item.value"
                    @mouseleave="hoverKey = ''"
                    :class="[activeIndex === index ? 'active' : '', item.isEdit ? 'is-edit' : '']">
                    <div class="label-item flex-row justify-content-between align-items-center" v-if="item.isEdit">
                      <bk-input
                        ref="editFileInputRef"
                        :placeholder="$t('请输入')"
                        v-model="item.value"
                        @blur="handleBlur(item, index)"
                        @enter="handleEnter('edit')"
                      ></bk-input>
                    </div>
                    <div
                      class="label-item flex-row justify-content-between"
                      @click.stop="handleClickLabelItem(index, item.value)" v-else>
                      <div class="label-text flex-1">
                        {{item.value}}
                        <i
                          v-if="!volumeFormData.source_config_data[item.value]"
                          class="icon paasng-icon paasng-paas-remind-fill tips-icon"
                          v-bk-tooltips="$t('文件内容不可为空')"></i>
                      </div>
                      <div class="label-icon flex-row align-items-center" v-if="hoverKey === item.value">
                        <i class="paasng-icon paasng-edit2" @click="handleEditLabel(item)" />
                        <i class="icon paasng-icon paasng-icon-close" @click="handleDeleteLabel(item.value, index)" />
                      </div>
                    </div>
                  </div>
                </div>
                <div class="editor flex-1">
                  <resource-editor
                    ref="editorRefSlider"
                    key="editor"
                    v-model="sliderEditordetail"
                    v-bkloading="{ isDiaLoading, opacity: 1, color: '#1a1a1a' }"
                    :height="fullScreen ? clientHeight : fileSliderConfig.height"
                  />
                </div>
              </div>
            </bk-form-item>
          </bk-form>
        </div>
      </div>
      <div slot="footer" class="ml30">
        <bk-button class="mr10" theme="primary" @click="handleConfirmVolume" :loading="addLoading">
          {{ $t('确定') }}
        </bk-button>
        <bk-button theme="default" @click="handleCancelVolume()">{{ $t('取消') }}</bk-button>
      </div>
    </bk-sideslider>
  </div>
</template>

<script>
import { cloneDeep } from 'lodash';
import appBaseMixin from '@/mixins/app-base-mixin';
import ResourceEditor from './comps/deploy-resource-editor';
// import i18n from '@/language/i18n.js';
import { ENV_ENUM } from '@/common/constants';
import { isJsonString } from '@/common/utils';

export default {
  components: {
    ResourceEditor,
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
      // 编辑器上面
      addFileInput: '',
      isAddFile: false,
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
            regex: /^\/([^/\0]+(\/)?)*$/,
            message: this.$t('请输入以斜杆(/)开头，且不包含空字符串的路径'),
            trigger: 'blur',
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
        source_config_data: {},
        source_type: 'ConfigMap',
        sourceConfigArrData: [],
      },
      envSelectList: [
        { value: '_global_', text: this.$t('所有环境') },
        { value: 'stag', text: this.$t('仅预发布环境') },
        { value: 'prod', text: this.$t('仅生产环境') },
      ],
      envEnums: ENV_ENUM,
      activeIndex: 0,
      hoverKey: '',
      curValue: '',
      addLoading: false,
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
  watch: {
    'volumeDefaultSettings.isShow'(v) {
      if (v) {
        this.sliderEditordetail = '';
        this.isAddFile = false;
        this.curValue = '';
        this.volumeFormData.sourceConfigArrData = (Object.keys(this.volumeFormData.source_config_data) || [])
          .reduce((p, v) => {
            p.push({
              value: v,
              isEdit: false,
            });
            return p;
          }, []);
        // 重置数据
        this.resetData();
      }
    },
    // 监听编辑器的值
    sliderEditordetail() {
      this.$nextTick(() => {
        if (!this.curValue) return;
        // 取值放入source_config_data中
        const editValue = this.$refs.editorRefSlider?.getValue();
        this.$set(this.volumeFormData.source_config_data, this.curValue, editValue);
      });
    },
  },
  mounted() {
    this.init();
  },
  methods: {
    // 重置数据
    resetData() {
      if (!this.volumeFormData.sourceConfigArrData.length) return;
      this.curValue = this.volumeFormData.sourceConfigArrData[0].value || '';
      const initValue = this.volumeFormData.source_config_data[this.curValue];
      this.activeIndex = 0;
      this.handleSetEditValue(initValue);
    },
    init() {
      this.isLoading = true;
      this.getVolumeList();
    },
    // 新增挂载
    handleCreate() {
      this.volumeFormData = {
        name: '',
        mount_path: '',
        environment_name: 'stag',
        source_config_data: {},
        source_type: 'ConfigMap',
        sourceConfigArrData: [],
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
        })
        .finally(() => {
          this.isLoading = false;
        });
    },
    // 编辑挂载券
    handleEditVolume(row) {
      this.volumeFormData = cloneDeep(row);
      this.$set(this.volumeFormData, 'sourceConfigArrData', []);
      this.volumeDefaultSettings.isShow = true;
    },
    // 确认删除挂载券
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
    // 删除挂载卷
    handleDelete(row) {
      this.$bkInfo({
        title: this.$t('确认删除挂载卷：') + row.name,
        confirmFn: () => {
          this.deleteVolume(row);
        },
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
      this.$refs.resourceEditorRef?.setValue(resultFormatDetail);
    },
    // 筛选生效环境
    sourceFilterMethod(value, row, column) {
      const { property } = column;
      return row[property] === value;
    },
    // 确定新增或编辑挂载券
    async handleConfirmVolume() {
      await this.$refs.formRef?.validate();
      try {
        this.addLoading = true;
        const fetchUrl = this.volumeFormData.id ? 'deploy/updateVolumeData' : 'deploy/createVolumeData';
        const param = {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          data: this.volumeFormData,
        };
        // 更新
        if (this.volumeFormData.id) {
          param.id = this.volumeFormData.id;
        }
        await this.$store.dispatch(
          fetchUrl,
          param,
        );
        this.volumeDefaultSettings.isShow = false;
        this.$paasMessage({
          theme: 'success',
          message: this.volumeFormData.id ? this.$t('更新成功') : this.$t('新增成功'),
        });
        this.getVolumeList();
      } catch (error) {
        this.$paasMessage({
          theme: 'error',
          message: error.detail,
        });
      } finally {
        this.addLoading = false;
      }
    },
    // 取消新增或编辑挂载券
    handleCancelVolume() {
      this.volumeDefaultSettings.isShow = false;
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
    // 添加文件
    handleAddFile() {
      this.isAddFile = true;
      this.addFileInput = '';
      this.$nextTick(() => {
        this.$refs.addFileInputRef.focus();
      });
    },
    // 失去焦点添加
    handlerAddConfirm() {
      // 没有内容时 return
      if (!this.addFileInput) {
        this.isAddFile = false;
        return;
      };
      const isValueRepeat = this.volumeFormData.sourceConfigArrData.find(e => e.value === this.addFileInput);
      // 有相同名称的文件名
      if (isValueRepeat) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('文件名重复'),
        });
        // this.$refs.addFileInputRef.focus();
        // this.isAddFile = false;
        return;
      }
      this.volumeFormData.sourceConfigArrData.unshift({ value: this.addFileInput, isEdit: false });
      // 选中第一条
      this.isAddFile = false;
      this.activeIndex = 0;
      this.curValue = this.addFileInput;
      this.sliderEditordetail = '';
      this.$nextTick(() => {
        this.$refs.editorRefSlider?.setValue('');
      });
    },
    // 文件名失焦
    handleBlur(item, index) {
      const sourceConfigArrData = cloneDeep(this.volumeFormData.sourceConfigArrData);
      sourceConfigArrData.splice(index, 1);
      const isValueRepeat = sourceConfigArrData.find(e => e.value === item.value);
      if (isValueRepeat) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('文件名重复'),
        });
        item.value = this.curValue;
        return;
      }
      item.isEdit = false;
      // 将之前的key对应的数据赋值给新的key并删除旧的key
      this.volumeFormData.source_config_data[item.value] = this.volumeFormData.source_config_data[this.curValue];
      if (item.value !== this.curValue) {
        delete this.volumeFormData.source_config_data[this.curValue];
      }
      this.curValue = item.value; // 失焦时需要更新curValue的值, 编辑右边yaml时有用到
    },

    // 处理回车键
    handleEnter(type) {
      if (type === 'add') {
        this.$nextTick(() => {
          this.$refs.addFileInputRef.blur();
        });
      } else {
        this.$nextTick(() => {
          this.$refs?.editFileInputRef[0].blur();
        });
      }
    },

    // 点击label
    handleClickLabelItem(i, key) {
      // 当前点击的文件名
      this.curValue = cloneDeep(key);
      this.activeIndex = i;
      this.volumeFormData.sourceConfigArrData.forEach(e => e.isEdit = false);
      // 设置值
      this.handleSetEditValue(this.volumeFormData.source_config_data[key]);
      // 判断是否是json字符串
      const isJsonStr = isJsonString(this.volumeFormData.source_config_data[key]);
      this.sliderEditordetail = isJsonStr
        ? JSON.parse(this.volumeFormData.source_config_data[key]) : this.volumeFormData.source_config_data[key];
      this.$refs.editorRefSlider?.setValue(this.sliderEditordetail);
    },

    // 删除一条左边的lable数据
    handleDeleteLabel(k, i) {
      this.volumeFormData.sourceConfigArrData.splice(i, 1);
      delete this.volumeFormData.source_config_data[k];
      setTimeout(() => {
        this.resetData();
      }, 10);
    },
    // 编辑左边的lable数据
    handleEditLabel(item) {
      this.volumeFormData.sourceConfigArrData.forEach(e => e.isEdit = false);
      setTimeout(() => {
        item.isEdit = true;
        this.$nextTick(() => {
          this.$refs?.editFileInputRef[0].focus();
        });
      }, 10);
      // 当前编辑的文件名
      this.$nextTick(() => {
        this.curValue = item.value;
      });
    },

    // 设置编辑器中的值
    handleSetEditValue(value) {
      // 判断是否是json字符串
      const isJsonStr = isJsonString(value);
      this.sliderEditordetail = isJsonStr
        ? JSON.stringify(JSON.parse(value)) : value;
      this.$refs.editorRefSlider?.setValue(this.sliderEditordetail);
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

.header-sub-name{
  color: #979ba5 !important;
  font-size: 14px;
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
          .file-container{
            background-color: #f5f7fa;
            .label-container{
              width: 200px;
              .addFile {
                color: #3a84ff;
                height: 40px;
                line-height: 40px;
                cursor: pointer;
                .addFileText{
                  padding: 0 24px;
                }
                .addFileInput {
                  padding: 0 12px;
                }
              }
              .label-container{
                color: #63656E;
                height: 40px;
                line-height: 40px;
                padding: 0 20px;
                cursor: pointer;
                .label-item{
                  width: 100%;
                }
                .label-text{
                  padding-left: 4px;
                  .tips-icon{
                    color: #ea3636;
                  }
                }
                .paasng-icon-close {
                  cursor: pointer;
                  font-size: 24px;
                }
                &:hover{
                  background: #F0F1F5;
                }
              }
              .label-container.active{
                color: #3a84ff;
                border-left: 4px solid #3A84FF;
                background: #fff;
                .label-text{
                  padding-left: 0px;
                }
              }
              .is-edit{
                padding: 0 12px;
              }
            }
            .editor {
              flex: 1;
            }
          }
        }
      }
    }
  }
}
</style>
