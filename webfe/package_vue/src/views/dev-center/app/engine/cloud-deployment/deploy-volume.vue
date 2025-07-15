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
      <FunctionalDependency
        :show-dialog.sync="showFunctionalDependencyDialog"
        mode="dialog"
        :title="$t('暂无持久存储功能')"
        :functional-desc="
          $t(
            '开发者中心的持久存储功能为多个模块和进程提供了一个共享的数据源，实现了数据的共享与交互，并确保了数据在系统故障或重启后的持久化和完整性。'
          )
        "
        :guide-title="$t('如需使用该功能，需要：')"
        :guide-desc-list="[$t('1. 在应用集群创建 StorageClass 并注册到开发者中心'), $t('2. 给应用开启持久存储特性')]"
        @gotoMore="gotoMore"
      />
      <section v-show="!isLoading">
        <bk-alert type="info">
          <span slot="title">
            {{
              $t(
                '挂载负责将内容挂载到进程文件系统中，当前支持“文件”和“持久存储”两种类型；文件常用于存储模块配置文件；持久存储提供一个持久化的存储空间，可跨模块和进程共享数据。'
              )
            }}
          </span>
        </bk-alert>
        <bk-button
          theme="primary"
          class="mb15 mt20"
          @click="handleCreate"
        >
          <i class="paasng-icon paasng-plus mr5" />
          {{ $t('新增挂载') }}
        </bk-button>
        <bk-table
          :data="volumeList"
          size="small"
          style="width: 100%"
          :outer-border="false"
          :header-border="false"
          v-bkloading="{ isLoading: isTableLoaing, zIndex: 10 }"
        >
          <bk-table-column
            :label="$t('名称')"
            prop="name"
          ></bk-table-column>
          <bk-table-column
            :label="$t('挂载目录')"
            prop="mount_path"
          ></bk-table-column>
          <bk-table-column
            :label="$t('启用子路径挂载')"
            prop="mount_path"
            :render-header="renderHeader"
          >
            <template slot-scope="{ row }">
              <span v-if="row.source_type === 'PersistentStorage'">--</span>
              <span v-else>{{ row.sub_paths.length ? $t('是') : $t('否') }}</span>
            </template>
          </bk-table-column>
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
          <bk-table-column
            :label="$t('资源类型')"
            :filters="resourceTypeFilterList"
            :filter-method="resourceTypeFilterMethod"
            :filter-multiple="false"
            prop="source_type"
          >
            <template slot-scope="{ row }">
              {{ row.source_type === 'PersistentStorage' ? $t('持久存储') : $t('文件') }}
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('文件内容')"
            width="400"
            prop="source_config_data"
          >
            <template slot-scope="{ row, $index }">
              <div class="tag-container">
                <!-- 持久存储 -->
                <template v-if="row.source_type === 'PersistentStorage'">
                  <bk-tag
                    v-for="item in visibleTags(row)"
                    :key="item"
                    class="activeTag"
                    v-bk-tooltips="{ content: item, disabled: item.length < 12 }"
                    @click="handlePersistentStorageDetails(row, item)"
                  >
                    {{ item.length > 12 ? `${item.slice(0, 12)}...` : item }}
                  </bk-tag>
                </template>
                <!-- 文件 -->
                <template v-else>
                  <bk-tag
                    v-for="item in visibleTags(row)"
                    :key="item"
                    class="activeTag file-tag"
                    @click="handleTag(row, item)"
                  >
                    {{ item }}
                  </bk-tag>
                  <!-- tooltips 显示模板 -->
                  <div
                    id="tooltipContent"
                    v-if="getCourceConfigDataLength(row) !== visibleTags(row).length"
                  >
                    <bk-tag
                      class="activeTag"
                      v-for="item in formatConfigData(row)"
                      :key="item"
                      @click="handleTag(row, item)"
                    >
                      {{ item }}
                    </bk-tag>
                  </div>
                  <a
                    v-if="getCourceConfigDataLength(row) !== visibleTags(row).length"
                    :ref="`tooltipContent${$index}`"
                    class="plusIcon"
                    v-bk-tooltips="tagTipConfig"
                  >
                    <bk-tag :key="'more'">+{{ getCourceConfigDataLength(row) - visibleTags(row).length }}</bk-tag>
                  </a>
                </template>
              </div>
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('操作')">
            <template slot-scope="props">
              <bk-button
                class="mr10"
                theme="primary"
                text
                @click="handleEditVolume(props.row)"
              >
                {{ $t('编辑') }}
              </bk-button>
              <bk-button
                class="mr10"
                theme="primary"
                text
                @click="handleDelete(props.row)"
              >
                {{ $t('删除') }}
              </bk-button>
            </template>
          </bk-table-column>
        </bk-table>
      </section>
    </paas-content-loader>
    <!-- 文件内容详情 -->
    <bk-dialog
      v-model="fileDialogConfig.visiable"
      :width="fileDialogConfig.dialogWidth"
      :position="{ top: fileDialogConfig.top }"
      theme="primary"
      header-position="left"
      :title="$t('文件内容详情')"
      :show-footer="false"
    >
      <resource-editor
        ref="resourceEditorRef"
        key="editor"
        v-model="detail"
        readonly
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
      :before-close="handleBeforeClose"
      @hidden="handleHidden"
    >
      <div slot="header">
        {{ volumeFormData.id ? $t('编辑') : $t('新增') }}{{ $t('挂载') }}
        <span class="header-sub-name pl5">
          {{ volumeFormData.name }}
        </span>
      </div>
      <div slot="content">
        <div class="slider-volume-content">
          <bk-alert
            type="info"
            class="mb10"
            :title="$t('新增或修改挂载后，需重新部署对应环境才能生效。')"
          ></bk-alert>
          <bk-form
            :label-width="200"
            form-type="vertical"
            :model="volumeFormData"
            ref="formRef"
          >
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
                :placeholder="mountPathTip"
              ></bk-input>
            </bk-form-item>
            <bk-form-item
              :label="$t('资源类型')"
              :required="true"
              style="width: 560px; margin-top: 15px"
              :property="'source_type'"
            >
              <bk-radio-group v-model="volumeFormData.source_type">
                <div
                  :class="[
                    'radio-style-wrapper',
                    { active: volumeFormData.source_type === 'ConfigMap' },
                    { disabled: isInEditMode },
                  ]"
                  @click="handleChangeSourceType('ConfigMap')"
                >
                  <bk-radio
                    :value="'ConfigMap'"
                    :disabled="isInEditMode"
                  >
                    {{ $t('文件') }}
                  </bk-radio>
                  <span class="tip">{{ $t('可用于将自定义的配置文件注入到进程内文件系统中') }}</span>
                </div>
                <div
                  v-bk-tooltips.bottom="{
                    content: $t(`暂不支持持久存储，请联系管理员开启“持久存储挂载卷”应用特性`),
                    disabled: !isClusterPersistentStorageSupported || enablePersistentStorage,
                  }"
                  :class="[
                    'radio-style-wrapper',
                    { active: volumeFormData.source_type === 'PersistentStorage' },
                    { disabled: isInEditMode || !enablePersistentStorage || !isClusterPersistentStorageSupported },
                  ]"
                  @click="handleChangeSourceType('PersistentStorage')"
                >
                  <bk-radio
                    :value="'PersistentStorage'"
                    :disabled="isInEditMode || !enablePersistentStorage || !isClusterPersistentStorageSupported"
                  >
                    {{ $t('持久存储') }}
                  </bk-radio>
                  <span class="tip">{{ $t('由平台分配的持久存储，可用于模块和进程间共享数据') }}</span>
                </div>
              </bk-radio-group>
            </bk-form-item>
            <bk-form-item
              v-if="!isPersistentStorage"
              :label="$t('启用子路径挂载')"
              :required="true"
            >
              <bk-switcher
                v-model="enableSubpathMount"
                theme="primary"
              ></bk-switcher>
              <span class="tip ml5">
                {{ subpathTip }}
              </span>
            </bk-form-item>
            <bk-form-item
              :label="$t('生效环境')"
              :required="true"
              style="margin-top: 27px"
              :property="'environment_name'"
            >
              <bk-radio-group
                v-model="volumeFormData.environment_name"
                @change="handleEnvironmentChange"
              >
                <bk-radio
                  :value="'stag'"
                  :disabled="isInEditMode && isPersistentStorage"
                >
                  {{ $t('仅预发布环境') }}
                </bk-radio>
                <bk-radio
                  :value="'prod'"
                  :disabled="isInEditMode && isPersistentStorage"
                >
                  {{ $t('仅生产环境') }}
                </bk-radio>
                <bk-radio
                  v-if="!isPersistentStorage"
                  :value="'_global_'"
                >
                  {{ $t('所有环境') }}
                </bk-radio>
              </bk-radio-group>
            </bk-form-item>
            <bk-form-item
              v-if="!isPersistentStorage"
              :label="$t('文件内容')"
              :required="true"
              style="margin-top: 15px"
              :property="'source_config_data'"
              ext-cls="volume-file-content"
            >
              <div class="file-container flex-row">
                <div class="label-container">
                  <div class="addFile">
                    <div
                      class="addFileText"
                      v-if="!isAddFile"
                      @click="handleAddFile"
                    >
                      <i class="icon paasng-icon paasng-plus-circle-shape pr10" />
                      {{ $t('添加文件') }}
                    </div>
                    <div
                      class="addFileInput"
                      v-else
                    >
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
                    :class="[activeIndex === index ? 'active' : '', item.isEdit ? 'is-edit' : '']"
                  >
                    <div
                      class="label-item flex-row justify-content-between align-items-center"
                      v-if="item.isEdit"
                    >
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
                      @click.stop="handleClickLabelItem(index, item.value)"
                      v-else
                    >
                      <div class="label-text flex-1">
                        {{ item.value }}
                        <i
                          v-if="!volumeFormData.source_config_data[item.value]"
                          class="icon paasng-icon paasng-paas-remind-fill tips-icon"
                          v-bk-tooltips="$t('文件内容不能为空')"
                        ></i>
                      </div>
                      <div
                        class="label-icon flex-row align-items-center"
                        v-if="hoverKey === item.value"
                      >
                        <i
                          class="paasng-icon paasng-edit-2 mr5"
                          @click="handleEditLabel(item)"
                        />
                        <i
                          class="icon paasng-icon paasng-icon-close"
                          @click="handleDeleteLabel(item.value, index)"
                        />
                      </div>
                    </div>
                  </div>
                </div>
                <div class="editor flex-1">
                  <resource-editor
                    ref="editorRefSlider"
                    key="editor"
                    v-model="sliderEditordetail"
                    :readonly="readonly"
                    v-bkloading="{ isDiaLoading, opacity: 1, color: '#1a1a1a' }"
                    :height="fullScreen ? clientHeight : fileSliderConfig.height"
                  />
                </div>
              </div>
            </bk-form-item>
            <template v-else>
              <bk-form-item
                :label="$t('持久存储')"
                :required="true"
                style="margin-top: 27px"
                :property="'source_name'"
              >
                <bk-select
                  :disabled="false"
                  v-model="volumeFormData.source_name"
                  style="width: 560px"
                  searchable
                  :placeholder="persistentStorageTips"
                  ext-popover-cls="store-select-popover-custom"
                >
                  <bk-option
                    v-for="option in curEnvPersistentStorageList"
                    :key="option.name"
                    :id="option.name"
                    :name="option.display_name"
                  >
                    <div class="option-content">
                      <span
                        class="name"
                        :title="option.display_name"
                      >
                        {{ option.display_name }}
                      </span>
                      <span class="info">
                        {{
                          `(${$t('容量')}：${persistentStorageSizeMap[option.storage_size]}，
                        ${$t('已绑定模块')}：${option.bound_modules.length})`
                        }}
                      </span>
                    </div>
                  </bk-option>
                  <div
                    slot="extension"
                    class="create-persistent-storage-cls"
                  >
                    <div
                      class="content"
                      @click="createPersistentStorage"
                    >
                      <i class="bk-icon icon-plus-circle mr5"></i>
                      {{ $t('新增持久存储') }}
                    </div>
                    <div
                      class="content"
                      @click="viewPersistentStorage"
                    >
                      <i class="paasng-icon paasng-jump-link mr5"></i>
                      {{ $t('查看持久存储') }}
                    </div>
                    <div
                      class="refresh"
                      @click.stop="getPersistentStorageList"
                    >
                      <i
                        class="paasng-icon paasng-refresh-line"
                        v-if="!isPersistentStorageLoading"
                      />
                      <round-loading
                        class="round-loading-cls"
                        v-else
                      />
                    </div>
                  </div>
                </bk-select>
              </bk-form-item>
            </template>
          </bk-form>
        </div>
      </div>
      <div
        slot="footer"
        class="ml30"
      >
        <bk-button
          class="mr10"
          theme="primary"
          :loading="addLoading"
          @click="handleConfirm"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          theme="default"
          @click="handleCancelVolume()"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </bk-sideslider>

    <!-- 持久存储详情 -->
    <bk-dialog
      v-model="storageDetailsDialogConfig.visible"
      theme="primary"
      header-position="left"
      :width="480"
      :mask-close="false"
      :show-footer="false"
    >
      <div
        slot="header"
        class="storage-header-title"
      >
        {{ $t('持久存储详情') }}
        <span class="storage-header-sub-tip">
          {{ $t('容量') }}：
          <span>{{ storageDetailsDialogConfig.storage_size }}</span>
        </span>
      </div>
      <bk-table
        :data="storageDetailsDialogConfig.bound_modules"
        :outer-border="false"
        ext-cls="volume-store-module-table-cls"
      >
        <bk-table-column
          :label="$t('绑定模块')"
          prop="module"
          :width="150"
        ></bk-table-column>
        <bk-table-column
          :label="$t('挂载目录')"
          prop="path"
        ></bk-table-column>
      </bk-table>
    </bk-dialog>

    <!-- 新增持久存储 -->
    <create-persistent-storage-dailog
      v-model="persistentStorageDailogVisible"
      @get-list="getPersistentStorageList"
    />

    <!-- 删除挂载弹窗 -->
    <bk-dialog
      v-model="deleteMountConfig.visible"
      header-position="left"
      theme="primary"
      :width="620"
      :loading="true"
      :mask-close="false"
      :auto-close="false"
      :title="$t('确认删除挂载：') + deleteMountConfig.data.name"
    >
      <p>{{ $t('挂载删除后，需要重新部署对应环境才能生效。') }}</p>
      <bk-alert
        class="mt15"
        type="warning"
        :title="$t('请注意，此操作不会影响持久存储内的数据。如需删除数据请在“应用配置-持久存储”页面操作。')"
      ></bk-alert>
      <section slot="footer">
        <bk-button
          :theme="'primary'"
          :loading="deleteMountConfig.loading"
          @click="deleteVolume(deleteMountConfig.data)"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          :theme="'default'"
          class="mr10"
          @click="deleteMountConfig.visible = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </section>
    </bk-dialog>
  </div>
</template>

<script>
import { cloneDeep } from 'lodash';
import appBaseMixin from '@/mixins/app-base-mixin';
import ResourceEditor from './comps/deploy-resource-editor';
import { ENV_ENUM, PERSISTENT_STORAGE_SIZE_MAP } from '@/common/constants';
import { isJsonString } from '@/common/utils';
import sidebarDiffMixin from '@/mixins/sidebar-diff-mixin';
import createPersistentStorageDailog from '@/components/create-persistent-storage-dailog';
import FunctionalDependency from '@blueking/functional-dependency/vue2/index.umd.min.js';

const defaultSourceType = 'PersistentStorage';
const containerWidth = 400;
const tagWidth = 90;

export default {
  components: {
    ResourceEditor,
    createPersistentStorageDailog,
    FunctionalDependency,
  },
  mixins: [appBaseMixin, sidebarDiffMixin],
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
        extCls: 'ellipsis-display-tips-cls',
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
            // regex: /^\/([^/\0]+(\/)?)+$/,
            regex: /^\/[^/\0][^/\0]*(?:\/[^/\0][^/\0]*)*\/?$/,
            message: this.$t('请输入以斜杆(/)开头，且不包含空字符串的路径（不包括根目录 "/"）'),
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
        // 持久存储名
        source_name: '',
      },
      envSelectList: [
        { value: 'stag', text: this.$t('仅预发布环境') },
        { value: 'prod', text: this.$t('仅生产环境') },
      ],
      // 资源类型筛选列表
      resourceTypeFilterList: [
        { value: 'ConfigMap', text: this.$t('文件') },
        { value: 'PersistentStorage', text: this.$t('持久存储') },
      ],
      envEnums: ENV_ENUM,
      activeIndex: 0,
      hoverKey: '',
      curValue: '',
      addLoading: false,
      mountPathTip: this.$t('请输入以斜杆(/)开头，且不包含空字符串的路径（不包括根目录 "/"）'),
      persistentStorageList: [],
      persistentStorageDailogVisible: false,
      isPersistentStorageLoading: false,
      storageDetailsDialogConfig: {
        visible: false,
        bound_modules: [],
        storage_size: '1Gi',
      },
      maxTags: 0,
      isTableLoaing: false,
      isInEditMode: false,
      persistentStorageSizeMap: PERSISTENT_STORAGE_SIZE_MAP,
      deleteMountConfig: {
        visible: false,
        loading: false,
        data: {},
      },
      showFunctionalDependencyDialog: false,
      // 集群是否支持持久存储
      isClusterPersistentStorageSupported: false,
      // 启用子路径挂载
      enableSubpathMount: true,
      subpathTip: this.$t('未启用时，挂载目录将被完全替换；启用后，挂载目录下同名文件将被覆盖，其他文件将保持不变。'),
    };
  },
  computed: {
    formatConfigData() {
      return function (data) {
        const tags = data.configmap_source?.source_config_data || {};
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
      return function (data) {
        // 持久存储
        if (data.source_type === defaultSourceType) {
          const displayName = data.persistent_storage_source?.display_name;
          return displayName ? [displayName] : [];
        }
        // 文件
        let totalTagWidth = 0;
        let maxTags = 0;
        const maxPossibleTags = Math.floor(containerWidth / tagWidth);
        for (let i = 0; i < maxPossibleTags; i++) {
          if (totalTagWidth + tagWidth <= containerWidth) {
            totalTagWidth += tagWidth;
            // eslint-disable-next-line no-plusplus
            maxTags++;
          } else {
            break;
          }
        }
        const files = data.configmap_source?.source_config_data || {};
        const tags = Object.keys(files);
        return tags.slice(0, maxTags);
      };
    },
    isPersistentStorage() {
      return this.volumeFormData.source_type === defaultSourceType;
    },
    persistentStorageTips() {
      return this.$t('请选择{e}环境下的持久存储资源', {
        e: this.volumeFormData.environment_name === 'stag' ? this.$t('预发布') : this.$t('生产'),
      });
    },
    // 当前环境
    curEnvPersistentStorageList() {
      return this.persistentStorageList.filter((v) => v.environment_name === this.volumeFormData.environment_name);
    },
    readonly() {
      return this.volumeFormData.sourceConfigArrData?.length <= 0;
    },
    enablePersistentStorage() {
      return this.curAppInfo.feature?.ENABLE_PERSISTENT_STORAGE;
    },
  },
  watch: {
    'volumeDefaultSettings.isShow'(v) {
      if (v) {
        this.sliderEditordetail = this.readonly ? this.$t('请先在左侧添加文件后，再编辑文件内容') : '';
        this.isAddFile = false;
        this.curValue = '';
        if (this.volumeFormData.source_type === defaultSourceType) {
          this.volumeFormData.sourceConfigArrData = [];
          this.volumeFormData.source_config_data = {};
        }
        this.volumeFormData.sourceConfigArrData = (Object.keys(this.volumeFormData.source_config_data) || []).reduce(
          (p, v) => {
            p.push({
              value: v,
              isEdit: false,
            });
            return p;
          },
          []
        );
        // 重置数据
        this.resetData();
        this.initSidebarFormData(this.volumeFormData);
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
      if (!this.volumeFormData.sourceConfigArrData.length) {
        this.handleSetEditValue(this.$t('请先在左侧添加文件后，再编辑文件内容'));
        return;
      }
      this.curValue = this.volumeFormData.sourceConfigArrData[0].value || '';
      const initValue = this.volumeFormData.source_config_data[this.curValue];
      this.activeIndex = 0;
      this.handleSetEditValue(initValue);
    },
    init() {
      this.isLoading = true;
      this.getClusterPersistentStorageFeature();
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
        source_name: '',
      };
      this.isInEditMode = false;
      this.volumeDefaultSettings.isShow = true;
      this.initSidebarFormData(this.volumeFormData);
    },
    // 获取挂载list
    getVolumeList() {
      this.isTableLoaing = true;
      const url = `${BACKEND_URL}/api/bkapps/applications/${this.appCode}/modules/${this.curModuleId}/mres/volume_mounts/`;
      this.$http
        .get(url)
        .then((res) => {
          this.volumeList = res.results;
        })
        .catch((e) => {
          this.$paasMessage({
            theme: 'error',
            message: e.detail || e.message || this.$t('接口异常'),
          });
        })
        .finally(() => {
          this.isLoading = false;
          this.isTableLoaing = false;
        });
    },
    // 编辑挂载券
    async handleEditVolume(row) {
      this.volumeFormData = cloneDeep(row);
      // 文件
      if (row.source_type === 'ConfigMap') {
        this.$set(this.volumeFormData, 'sourceConfigArrData', []);
        this.volumeFormData.source_config_data = row.configmap_source?.source_config_data || {};
        this.enableSubpathMount = !!row.sub_paths?.length;
      } else {
        this.volumeFormData.source_name = row.persistent_storage_source?.name;
        this.getPersistentStorageList();
      }
      this.isInEditMode = true;
      this.volumeDefaultSettings.isShow = true;
      await this.getPersistentStorageList();
      this.initSidebarFormData(this.volumeFormData);
    },
    // 确认删除挂载券
    deleteVolume(row) {
      this.deleteMountConfig.loading = true;
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
          this.deleteMountConfig.loading = false;
          this.deleteMountConfig.visible = false;
          this.getVolumeList();
        });
    },
    // 删除挂载
    handleDelete(row) {
      if (row.source_type === defaultSourceType) {
        this.deleteMountConfig.visible = true;
        this.deleteMountConfig.data = row;
        return;
      }

      this.$bkInfo({
        extCls: 'delete-volume-info-cls',
        okText: this.$t('确定'),
        cancelText: this.$t('取消'),
        title: this.$t('确认删除挂载：') + row.name,
        subTitle: this.$t('挂载删除后，需要重新部署对应环境才能生效。'),
        confirmFn: () => {
          this.deleteVolume(row);
        },
      });
    },
    // 点击标签
    handleTag(row, item) {
      if (row.source_type === defaultSourceType) {
        return;
      }
      row = row.configmap_source?.source_config_data || {};
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
      if (window.innerWidth < 1366) {
        this.fileDialogConfig.dialogWidth = 800;
        this.fileDialogConfig.top = 80;
        this.fileDialogConfig.height = 400;
      } else {
        this.fileDialogConfig.dialogWidth = 1100;
        this.fileDialogConfig.top = 120;
        this.fileDialogConfig.height = 520;
      }
    },
    // 筛选生效环境
    sourceFilterMethod(value, row, column) {
      const { property } = column;
      return row[property] === value;
    },
    resourceTypeFilterMethod(value, row, column) {
      const { property } = column;
      return row[property] === value;
    },
    // 格式化参数
    formatParams() {
      const data = cloneDeep(this.volumeFormData);
      // 持久存储
      if (this.isPersistentStorage) {
        const curStorage = this.persistentStorageList.find((v) => v.name === this.volumeFormData.source_name);
        data.environment_name = curStorage.environment_name;
        delete data.sourceConfigArrData;
        delete data.source_config_data;
      } else {
        data.configmap_source = {
          source_config_data: data.source_config_data,
        };
        data.sub_paths = this.enableSubpathMount ? Object.keys(data.source_config_data) : [];
        delete data.source_config_data;
      }

      const params = {
        appCode: this.appCode,
        moduleId: this.curModuleId,
        data,
      };
      // 更新
      if (this.volumeFormData.id) {
        params.id = this.volumeFormData.id;
      }
      return params;
    },
    handleConfirm() {
      this.$refs.formRef
        ?.validate()
        .then(() => {
          if (!this.isPersistentStorage) {
            if (!Object.keys(this.volumeFormData?.source_config_data || {})?.length) {
              this.$paasMessage({
                theme: 'error',
                message: this.$t('请填写文件名'),
              });
              return;
            }
            if (!this.sliderEditordetail) {
              this.$paasMessage({
                theme: 'error',
                message: this.$t('挂载内容不可为空'),
              });
              return;
            }
          }
          this.handleConfirmVolume();
        })
        .catch((e) => {
          console.error(e);
        });
    },
    // 确定新增或编辑挂载券
    async handleConfirmVolume() {
      try {
        this.addLoading = true;
        const fetchUrl = this.volumeFormData.id ? 'deploy/updateVolumeData' : 'deploy/createVolumeData';
        const params = this.formatParams();
        await this.$store.dispatch(fetchUrl, params);
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
    // 取消编辑
    async handleCancelVolume() {
      const isClosed = await this.handleBeforeClose();
      if (!isClosed) {
        return;
      }
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
      }
      const isValueRepeat = this.volumeFormData.sourceConfigArrData.find((e) => e.value === this.addFileInput);
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
      const isValueRepeat = sourceConfigArrData.find((e) => e.value === item.value);
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
      this.$refs.editorRefSlider?.handleFocus();
    },

    // 点击label
    handleClickLabelItem(i, key) {
      // 当前点击的文件名
      this.curValue = cloneDeep(key);
      this.activeIndex = i;
      this.volumeFormData.sourceConfigArrData.forEach((e) => (e.isEdit = false));
      // 设置值
      this.handleSetEditValue(this.volumeFormData.source_config_data[key]);
      // 判断是否是json字符串
      const isJsonStr = isJsonString(this.volumeFormData.source_config_data[key]);
      this.sliderEditordetail = isJsonStr
        ? JSON.parse(this.volumeFormData.source_config_data[key])
        : this.volumeFormData.source_config_data[key];
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
      this.volumeFormData.sourceConfigArrData.forEach((e) => (e.isEdit = false));
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
      this.sliderEditordetail = isJsonStr ? JSON.stringify(JSON.parse(value)) : value;
      this.$refs.editorRefSlider?.setValue(this.sliderEditordetail);
    },

    async handleBeforeClose() {
      return this.$isSidebarClosed(JSON.stringify(this.volumeFormData));
    },

    getCourceConfigDataLength(row) {
      const files = row.configmap_source?.source_config_data || {};
      return Object.keys(files).length;
    },

    // 持久存储详情
    handlePersistentStorageDetails(row) {
      this.storageDetailsDialogConfig.visible = true;
      this.storageDetailsDialogConfig.bound_modules = row.persistent_storage_source?.bound_modules || [];
      this.storageDetailsDialogConfig.storage_size = row.persistent_storage_source?.storage_size || '1Gi';
    },

    // 获取持久化存储列表
    async getPersistentStorageList() {
      if (this.isPersistentStorageLoading) {
        return;
      }
      this.isPersistentStorageLoading = true;
      try {
        const res = await this.$store.dispatch('persistentStorage/getPersistentStorageList', {
          appCode: this.appCode,
          sourceType: defaultSourceType,
        });
        this.persistentStorageList = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          this.isPersistentStorageLoading = false;
        }, 500);
      }
    },

    // 新增持久存储
    createPersistentStorage() {
      this.persistentStorageDailogVisible = true;
    },

    viewPersistentStorage() {
      this.$router.push({
        name: 'appPersistentStorage',
      });
    },

    // 切换资源类型
    handleChangeSourceType(value) {
      // 编辑态不允许切换
      if (this.isInEditMode) return;
      if (value === defaultSourceType) {
        // 集群特性未开启
        if (!this.isClusterPersistentStorageSupported) {
          this.showFunctionalDependencyDialog = true;
          return;
        }
        // 应用特性未开启
        if (!this.enablePersistentStorage) return;
      }
      this.volumeFormData.source_type = value;
      if (value === defaultSourceType && !this.persistentStorageList.length) {
        this.getPersistentStorageList();
      }
    },

    handleHidden() {
      this.isInEditMode = false;
      this.persistentStorageList = [];
      this.enableSubpathMount = true;
    },

    // 切换生效环境
    handleEnvironmentChange() {
      if (this.isPersistentStorage) {
        this.volumeFormData.source_name = '';
      }
    },

    // 获取集群特性
    async getClusterPersistentStorageFeature() {
      try {
        const res = await this.$store.dispatch('persistentStorage/getClusterPersistentStorageFeature', {
          appCode: this.appCode,
        });
        this.isClusterPersistentStorageSupported = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    gotoMore() {
      const baseDocUrl = this.GLOBAL.LINK.BK_APP_DOC?.endsWith('/')
        ? this.GLOBAL.LINK.BK_APP_DOC
        : `${this.GLOBAL.LINK.BK_APP_DOC}/`;
      const docUrl = `${baseDocUrl}topics/paas/paas_persistent_storage`;
      window.open(docUrl, '_blank');
    },

    renderHeader(h, data) {
      const directive = {
        name: 'bkTooltips',
        content: this.subpathTip,
        width: 300,
        placement: 'top',
      };
      return (
        <span
          class="custom-header-cell"
          v-bk-tooltips={directive}
        >
          {data.column.label}
        </span>
      );
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
      height: calc(100% - 102px);
    }
  }
  .bk-sideslider-footer {
    border-top: 1px solid #dcdee5 !important;
    background: #fafbfd !important;
  }
}
.delete-volume-info-cls .bk-dialog-header-inner {
  word-break: break-word !important;
}
.store-select-popover-custom .bk-select-extension {
  padding: 0 10px;
}
.ellipsis-display-tips-cls .tippy-tooltip {
  padding: 8px !important;
  .bk-tag:first-child {
    cursor: pointer;
    &:first-child {
      margin-left: 0px;
    }
  }
}
.volume-store-module-table-cls.bk-table table {
  width: 432px !important;
}
.fuctional-deps-modal-ctx.is-show {
  z-index: 99999 !important;
}
</style>

<style lang="scss" scoped>
.volume-container {
  padding: 0 20px 20px;
  min-height: 200px;
  .tip {
    font-size: 12px;
    color: #979ba5;
  }
  /deep/ .bk-table-header .custom-header-cell {
    color: inherit;
    text-decoration: underline;
    text-decoration-style: dashed;
    text-underline-position: under;
    text-decoration-color: #979ba5;
  }
}
.activeTag:hover {
  color: #3a84ff;
}

.header-sub-name {
  color: #979ba5 !important;
  font-size: 14px;
}

.label-icon i {
  cursor: pointer;
  font-size: 12px;
  color: #979ba5;
  padding: 3px;

  &:hover {
    color: #3a84ff;
  }
}

.radio-style-wrapper {
  display: flex;
  align-items: center;
  min-height: 40px;
  padding: 0 24px;
  background: #ffffff;
  border: 1px solid #c4c6cc;
  border-radius: 2px;
  cursor: pointer;

  label {
    flex-shrink: 0;
  }

  .tip {
    margin-left: 24px;
    font-size: 14px;
    color: #979ba5;
  }

  &.active {
    background: #e1ecff;
    border: 1px solid #3a84ff;
  }

  &.disabled {
    span {
      color: #c4c6cc;
    }
  }

  &:last-child {
    margin-top: 12px;
  }
}

.create-persistent-storage-cls {
  display: flex;
  align-items: center;
  .content {
    position: relative;
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    font-size: 12px;
    color: #63656e;
    cursor: pointer;
    i {
      font-size: 14px;
      transform: translateY(0px);
      color: #979ba5;
    }
    &:nth-child(2) {
      &::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 0;
        width: 1px;
        height: 23px;
        background: #dcdee5;
        transform: translateY(-50%);
      }
    }
  }
  .refresh {
    width: 20px;
    text-align: center;
    position: relative;
    cursor: pointer;
    &::before {
      content: '';
      position: absolute;
      top: 50%;
      left: -9px;
      width: 1px;
      height: 23px;
      background: #dcdee5;
      transform: translateY(-50%);
    }
    i {
      font-size: 14px;
      color: #63656e;
    }
  }
}

.storage-header-title {
  color: #313238;
  .storage-header-sub-tip {
    margin-left: 20px;
    font-size: 14px;
    color: #63656e;
    span {
      color: #313238;
    }
  }
}

.tag-container {
  & > .bk-tag:first-child {
    margin-left: 0px;
  }
  .bk-tag {
    cursor: pointer;
  }
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
          .file-container {
            background-color: #f5f7fa;
            .label-container {
              width: 200px;
              .addFile {
                color: #3a84ff;
                height: 40px;
                line-height: 40px;
                cursor: pointer;
                .addFileText {
                  padding: 0 24px;
                }
                .addFileInput {
                  padding: 0 12px;
                }
              }
              .label-container {
                color: #63656e;
                height: 40px;
                line-height: 40px;
                padding: 0 20px;
                cursor: pointer;
                .label-item {
                  width: 100%;
                }
                .label-text {
                  padding-left: 4px;
                  .tips-icon {
                    color: #ea3636;
                  }
                }
                .paasng-icon-close {
                  cursor: pointer;
                  font-size: 24px;
                }
                &:hover {
                  background: #f0f1f5;
                }
              }
              .label-container.active {
                color: #3a84ff;
                border-left: 4px solid #3a84ff;
                background: #fff;
                .label-text {
                  padding-left: 0px;
                }
              }
              .is-edit {
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
.store-select-popover-custom .option-content {
  display: flex;
  justify-content: space-between;
  .name {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .info {
    flex-shrink: 0;
  }
}
</style>
