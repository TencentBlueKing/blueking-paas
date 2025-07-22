<template>
  <div :class="['env-var-list-container', { 'hide-empty': !showEmpty }]">
    <bk-form
      ref="validateForm"
      :model="formData"
      :rules="rules"
      :label-width="0"
    >
      <!-- 环境变量列表 -->
      <bk-table
        ref="tableRef"
        :data="filteredVarList"
        size="small"
        class="env-var-table-cls"
        v-bkloading="{ isLoading: loading, zIndex: 10 }"
        @sort-change="handleSortChange"
      >
        <!-- 应用描述文件 -->
        <template slot="append">
          <slot name="append"></slot>
        </template>

        <!-- Key列 -->
        <bk-table-column
          prop="key"
          :render-header="handleRenderHander"
          :sortable="'custom'"
          :show-overflow-tooltip="true"
        >
          <template slot-scope="{ row, $index }">
            <div
              v-if="!row.isEditing"
              class="key-wrapper"
            >
              <div class="var-key">{{ row.key }}</div>
              <!-- 环境变量冲突提示 -->
              <i
                v-if="!!row.conflict?.message"
                :class="['paasng-icon paasng-remind', { warning: row.conflict?.overrideConflicted }]"
                v-bk-tooltips="{
                  content: row.conflict?.message,
                  width: 200,
                }"
              ></i>
            </div>
            <bk-form-item
              v-else
              :property="`varList.${$index}.key`"
              :rules="getKeyRules($index)"
            >
              <bk-input
                :ref="`keyInput${$index}`"
                v-model="row.key"
                placeholder="ENV_KEY"
                @keydown="(value, event) => handleKeyDown(`valueInput${$index}`, event)"
              ></bk-input>
            </bk-form-item>
          </template>
        </bk-table-column>

        <!-- 是否敏感列 -->
        <bk-table-column :render-header="handleRenderHander">
          <template slot-scope="{ row }">
            <bk-tag
              v-if="!row.isEditing"
              :theme="!!row.is_sensitive ? 'success' : ''"
            >
              {{ !!row.is_sensitive ? $t('是') : $t('否') }}
            </bk-tag>
            <bk-select
              v-else
              v-model="row.is_sensitive"
              :clearable="false"
              tabindex="-1"
              :disabled="!row.isNew && row.isEditing"
            >
              <bk-option
                v-for="option in isEncryptedSelectList"
                :id="option.value"
                :key="option.text"
                :name="option.text"
              />
            </bk-select>
          </template>
        </bk-table-column>

        <!-- Value列 -->
        <bk-table-column
          :render-header="handleRenderHander"
          :show-overflow-tooltip="true"
        >
          <template slot-scope="{ row, $index }">
            <span v-if="!row.isEditing">{{ !!row.is_sensitive ? DEFAULT_ENCRYPTED_VALUE : row.value }}</span>
            <bk-form-item
              v-else
              :property="`varList.${$index}.value`"
              :rules="rules.value"
            >
              <bk-input
                :ref="`valueInput${$index}`"
                v-model="row.value"
                placeholder="env_value"
                :password-icon="[]"
                :type="row.is_sensitive ? 'password' : 'text'"
                @focus="handleValueFocus(row)"
                @keydown="(value, event) => handleKeyDown(`descriptionInput${$index}`, event)"
              ></bk-input>
            </bk-form-item>
          </template>
        </bk-table-column>

        <!-- 环境列 -->
        <bk-table-column :render-header="handleRenderHander">
          <template slot-scope="{ row, $index }">
            <div v-if="!row.isEditing">
              {{ ENV_ENUM[row.environment_name] || $t('所有环境') }}
            </div>
            <bk-select
              v-else
              v-model="row.environment_name"
              :clearable="false"
              tabindex="-1"
              @change="handleEnvChange(row, $index)"
            >
              <bk-option
                v-for="option in envSelectList"
                :id="option.value"
                :key="option.text"
                :name="option.text"
              />
            </bk-select>
          </template>
        </bk-table-column>

        <!-- 描述列 -->
        <bk-table-column
          :render-header="handleRenderHander"
          :show-overflow-tooltip="true"
        >
          <template slot-scope="{ row, $index }">
            <span v-if="!row.isEditing">{{ row.description || '--' }}</span>
            <bk-form-item
              v-else
              :property="`varList.${$index}.description`"
              :rules="rules.description"
            >
              <bk-input
                :ref="`descriptionInput${$index}`"
                v-model="row.description"
                :placeholder="$t('输入描述文字，可选')"
                @keydown="(value, event) => handleKeyDown(`keyInput${$index}`, event)"
              ></bk-input>
            </bk-form-item>
          </template>
        </bk-table-column>

        <bk-table-column
          :label="$t('操作')"
          :width="140"
        >
          <template slot-scope="{ row, $index }">
            <!-- 批量编辑 -->
            <div
              v-if="isBatchEditing"
              class="env-table-icon"
            >
              <i
                class="icon paasng-icon paasng-plus-circle-shape"
                @click="batchAdd(row, $index)"
              ></i>
              <i
                class="icon paasng-icon paasng-minus-circle-shape"
                @click="batchDel(row, $index)"
              ></i>
            </div>
            <!-- 单条编辑 -->
            <div v-else>
              <template v-if="!row.isEditing">
                <bk-button
                  theme="primary"
                  text
                  class="mr10"
                  @click="toggleEdit(row, $index)"
                >
                  {{ $t('编辑') }}
                </bk-button>
                <bk-popconfirm
                  trigger="click"
                  width="288"
                  @confirm="handleDelete(row)"
                >
                  <div slot="content">
                    <div class="content-text mb10">{{ $t('确认删除该环境变量？') }}</div>
                  </div>
                  <bk-button
                    :text="true"
                    title="primary"
                  >
                    {{ $t('删除') }}
                  </bk-button>
                </bk-popconfirm>
              </template>
              <template v-else>
                <bk-button
                  theme="primary"
                  text
                  class="mr10"
                  @click="handleSave(row, $index)"
                >
                  {{ $t('保存') }}
                </bk-button>
                <bk-button
                  theme="primary"
                  text
                  @click="toggleEdit(row)"
                >
                  {{ $t('取消') }}
                </bk-button>
              </template>
            </div>
          </template>
        </bk-table-column>
      </bk-table>
    </bk-form>
  </div>
</template>

<script>
import { ENV_ENUM } from '@/common/constants';
import { cloneDeep } from 'lodash';

export default {
  name: 'EnvVarList',
  props: {
    list: {
      type: Array,
      default: () => [],
    },
    active: {
      type: String,
      default: 'all',
    },
    loading: {
      type: Boolean,
      default: false,
    },
    // 是否展示表格无数据时的空状态
    showEmpty: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      varList: [],
      formData: {
        varList: [],
      },
      isEncryptedSelectList: [
        { value: 1, text: this.$t('是') },
        { value: 0, text: this.$t('否') },
      ],
      envSelectList: [
        { value: '_global_', text: this.$t('所有环境') },
        { value: 'stag', text: this.$t('预发布环境') },
        { value: 'prod', text: this.$t('生产环境') },
      ],
      ENV_ENUM,
      // 加密后 Value 的默认值。与接口一致
      DEFAULT_ENCRYPTED_VALUE: '******',
      // 批量编辑模式
      isBatchEditing: false,
      rules: {
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
            max: 200,
            message: this.$t('不能超过200个字符'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    // 根据筛选值过滤后的列表（兼容批量操作）
    filteredVarList() {
      let filteredList = [...this.varList];

      if (this.active !== 'all') {
        filteredList = filteredList.filter(
          (item) => item.environment_name === this.active || item.isNew || item.isBatchDeleted
        );
      }
      // 过滤掉标记为删除的行
      return filteredList.filter((item) => !item.isBatchDeleted);
    },
  },
  watch: {
    list: {
      handler() {
        this.initData();
      },
      immediate: true,
    },
    active: {
      handler() {
        this.syncFormDataWithFilteredList();
        this.cleanNewRows();
      },
      immediate: true,
    },
  },
  methods: {
    // 初始化数据
    initData() {
      this.varList = cloneDeep(this.list).map((item) => ({
        ...item,
        isEditing: false,
      }));
      this.syncFormDataWithFilteredList();
    },

    // 动态生成key的校验规则
    getKeyRules(index) {
      const baseRules = [
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
        {
          validator: (value) => this.validateDuplicateKey(value, index),
          message: this.$t('该环境下已存在相同KEY的变量'),
          trigger: 'blur',
        },
      ];
      return baseRules;
    },

    // 校验KEY是否重复
    validateDuplicateKey(value, index) {
      if (!value) return true;

      const currentRow = this.formData.varList[index];
      if (!currentRow || !currentRow.environment_name) return true;

      // 查找相同环境和KEY的行
      const duplicateCount = this.formData.varList.filter(
        (item, i) =>
          i !== index && // 排除当前行
          item.key === value &&
          item.environment_name === currentRow.environment_name &&
          !item.isBatchDeleted // 排除标记删除的行
      ).length;

      return duplicateCount === 0;
    },

    // 清除所有未保存的新建行
    cleanNewRows() {
      this.varList = this.varList.filter((item) => !item.isNew);
      this.formData.varList = this.formData.varList.filter((item) => !item.isNew);
    },

    // 同步表单数据与过滤后的列表
    syncFormDataWithFilteredList() {
      this.formData.varList = [...this.filteredVarList];
    },

    // 加密状态 & 编辑模式，focus时清除密码输入框的内容
    handleValueFocus(row) {
      if (!!row.is_sensitive && !row.isNew) {
        row.value = '';
      }
    },

    keyFocus($index) {
      this.$nextTick(() => {
        const keyInput = this.$refs[`keyInput${$index}`];
        if (keyInput && keyInput.focus) {
          keyInput.focus();
        }
      });
    },

    handleSortChange({ order, prop }) {
      const orderBy = prop === 'key' ? (order === 'ascending' ? 'key' : '-key') : 'created';
      this.$emit('sort', orderBy);
    },

    // 切换编辑状态
    toggleEdit(row, index) {
      this.cleanNewRows();
      // 如果当前行已经在编辑状态，直接取消编辑
      if (row.isEditing) {
        this.cancelEdit(row);
        this.syncFormDataWithFilteredList();
        return;
      }
      // 取消其他正在编辑的行
      this.cancelAllEditing();
      // 设置当前行进入编辑状态
      row.isEditing = true;
      this.keyFocus(index);
    },

    // 切换选中环境时，判断当前key是否已存在于该环境
    async handleEnvChange(row, index) {
      if (row.key) {
        this.$refs.validateForm.validateField(`varList.${index}.key`).catch((e) => {
          console.error('验证失败', e);
        });
      }
    },

    // 新建一行
    add() {
      // 取消所有现有编辑状态
      this.cancelAllEditing();

      const newRow = {
        key: '',
        value: '',
        is_sensitive: 0,
        environment_name: this.active === 'all' ? 'stag' : this.active,
        description: '',
        isEditing: true,
        isNew: true,
      };

      // 新行添加到开头
      this.varList.push(newRow);
      this.formData.varList.push(newRow);
      this.keyFocus(this.formData.varList.length - 1);
    },

    // 取消所有编辑状态
    cancelAllEditing() {
      const editingRows = [...this.varList].filter((item) => item.isEditing);
      editingRows.forEach((row) => {
        this.cancelEdit(row);
      });
    },

    // 取消单个编辑行
    cancelEdit(row) {
      if (row.isNew) {
        const index = this.varList.findIndex((item) => item === row);
        if (index !== -1) {
          this.varList.splice(index, 1);
          this.formData.varList.splice(index, 1);
        }
      } else {
        const originalData = this.list.find((item) => item.id === row.id) || {};
        Object.assign(row, originalData, { isEditing: false });
      }
    },

    // 过滤掉自定义属性
    getCleanVariable(row) {
      const { isEditing, isNew, is_sensitive, ...cleanData } = row;
      if (!isNew && !!is_sensitive && cleanData.value === this.DEFAULT_ENCRYPTED_VALUE) {
        delete cleanData.value;
      }
      if (this.isBatchEditing && typeof cleanData.id === 'string') {
        if (cleanData.id.startsWith('costum-')) {
          delete cleanData.id; // 删除批量添加的行的临时标记
        }
      }
      return {
        ...cleanData,
        is_sensitive: !!is_sensitive,
      };
    },

    // 保存校验单行环境变量
    async handleSave(row, index) {
      try {
        // 验证表单
        const validateFields = [
          this.$refs.validateForm.validateField(`varList.${index}.key`),
          this.$refs.validateForm.validateField(`varList.${index}.value`),
          this.$refs.validateForm.validateField(`varList.${index}.description`),
        ];
        await Promise.all(validateFields);
        const data = this.getCleanVariable(row);
        if (row.isNew) {
          this.$emit('add', data, index);
        } else {
          this.$emit('update', data, index);
        }
        row.isEditing = false;
      } catch (e) {
        console.error('验证失败', e);
      }
    },

    // 删除行
    handleDelete(row) {
      this.$emit('delete', row);
    },

    handleRenderHander(h, { $index }) {
      const columns = ['Key', this.$t('是否敏感'), 'Value', this.$t('生效环境'), this.$t('描述')];
      const columnName = columns[$index] || 'Key';
      const isEncrypt = $index === 1;
      const directive = {
        content: this.$t('敏感环境变量的值将在页面上以脱敏形式展示，只有应用进程内能够获取到这些变量的明文值。'),
        width: 200,
        placement: 'top',
        disabled: !isEncrypt,
      };
      return (
        <span
          class={`flex-row align-items-center${isEncrypt ? ' is-encrypt' : ''}`}
          v-bk-tooltips={directive}
        >
          <span class="column-title">{columnName}</span>
          {[0, 1, 2, 3].includes($index) && <span class="header-required">*</span>}
        </span>
      );
    },

    // 开启批量编辑，编辑当前模块下的所有环境变量
    batchEdit() {
      this.$emit('batch-edit');
      this.isBatchEditing = true;
      this.varList.forEach((row) => {
        row.isEditing = true;
      });
      this.syncFormDataWithFilteredList();
    },

    // 批量添加新行
    batchAdd() {
      const newRow = {
        id: `costum-${Date.now()}`, // 使用时间戳作为唯一标识
        key: '',
        value: '',
        is_sensitive: 0,
        environment_name: 'stag',
        description: '',
        isEditing: true,
        isNew: true,
        isBatchAdded: true, // 标记为批量添加的行
      };

      // 在列表末尾追加新行
      this.varList.push(newRow);
      this.formData.varList.push(newRow);
    },

    // 批量删除行
    batchDel(row) {
      const deleteIndex = this.varList.findIndex(
        (item) => item.id === row.id && item.environment_name === row.environment_name
      );
      // 标记为批量删除状态
      this.$set(this.varList[deleteIndex], 'isBatchDeleted', true);
      this.syncFormDataWithFilteredList();
    },

    // 保存批量编辑、校验整个表单
    async saveBatchEdit() {
      try {
        // 数据没有变化，校验失败
        await this.$refs.validateForm.validate();
        const modifiedData = this.varList
          .filter((item) => !item.isBatchDeleted) // 过滤掉标记删除的项
          .map((row) => this.getCleanVariable(row));
        // 触发批量保存事件
        this.$emit('batch-save', modifiedData);
        this.batchCancel();
        return modifiedData;
      } catch (e) {
        throw new Error(e.content);
      }
    },

    // 取消批量编辑
    batchCancel() {
      this.isBatchEditing = false;
      this.initData();
    },

    // tab 聚焦对应 Input
    handleKeyDown(nextRef, event) {
      if (event.key === 'Tab') {
        event.preventDefault();
        this.$refs[nextRef]?.focus();
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.env-var-list-container {
  &.hide-empty .env-var-table-cls {
    /deep/ .bk-table-empty-block {
      display: none;
    }
  }
  .env-var-table-cls {
    /deep/ .bk-table-header {
      .is-encrypt .column-title {
        text-decoration: underline;
        text-decoration-style: dashed;
        text-underline-position: under;
      }
    }
    .key-wrapper {
      display: flex;
      align-items: center;
      i {
        margin-left: 5px;
        font-size: 14px;
        color: #ea3636;
        transform: translateY(0);
        &.warning {
          color: #ff9c01;
        }
      }
      .var-key {
        text-overflow: ellipsis;
        white-space: nowrap;
        overflow: hidden;
      }
    }
    .env-table-icon {
      i {
        padding: 5px;
        color: #c4c6cc;
        font-size: 14px;
        cursor: pointer;
      }
    }
  }
  /deep/ .bk-table-header-label {
    .header-required {
      color: #ea3636;
      padding-left: 5px;
      padding-top: 5px;
    }
  }
  /deep/ .bk-form-item {
    margin-bottom: 0;
  }
}
</style>
