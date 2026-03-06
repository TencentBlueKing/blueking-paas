<template>
  <div class="config-items-table">
    <bk-table
      :data="value"
      :outer-border="false"
      :header-border="false"
      :border="false"
      ext-cls="config-table-cls"
    >
      <template slot="empty">{{ $t('暂无数据') }}</template>
      <bk-table-column
        :label="$t('字段名')"
        prop="key"
        min-width="150"
      >
        <template slot-scope="{ row, $index }">
          <bk-form
            v-if="row.isEditing"
            :ref="`keyForm${$index}`"
            :model="row"
            :rules="keyRules"
            style="margin-bottom: 0"
          >
            <bk-form-item
              :property="'key'"
              style="margin-bottom: 0"
            >
              <bk-input
                v-model="row.key"
                :placeholder="$t('请输入字段名')"
              ></bk-input>
            </bk-form-item>
          </bk-form>
          <span v-else>{{ row.key || '--' }}</span>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('类型')"
        prop="type"
        width="120"
      >
        <template slot-scope="{ row }">
          <bk-select
            v-if="row.isEditing"
            v-model="row.type"
            :clearable="false"
          >
            <bk-option
              v-for="item in fieldTypeList"
              :key="item.id"
              :id="item.id"
              :name="item.name"
            ></bk-option>
          </bk-select>
          <span v-else>{{ row.type || '--' }}</span>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('必填')"
        prop="required"
        width="80"
      >
        <template slot-scope="{ row }">
          <bk-switcher
            v-if="row.isEditing"
            v-model="row.required"
            theme="primary"
          ></bk-switcher>
          <bk-tag
            v-else
            :theme="row.required ? 'danger' : 'default'"
          >
            {{ row.required ? $t('是') : $t('否') }}
          </bk-tag>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('示例')"
        prop="example"
        min-width="200"
      >
        <template slot-scope="{ row }">
          <bk-input
            v-if="row.isEditing"
            v-model="row.example"
            :placeholder="$t('请输入示例')"
          ></bk-input>
          <span v-else>{{ row.example || '--' }}</span>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('操作')"
        width="120"
      >
        <template slot-scope="{ row, $index }">
          <template v-if="row.isEditing">
            <bk-button
              text
              theme="primary"
              class="mr10"
              @click="handleSave($index)"
            >
              {{ $t('保存') }}
            </bk-button>
            <bk-button
              text
              @click="handleCancel($index)"
            >
              {{ $t('取消') }}
            </bk-button>
          </template>
          <template v-else>
            <bk-button
              text
              theme="primary"
              class="mr10"
              @click="handleEdit($index)"
            >
              {{ $t('编辑') }}
            </bk-button>
            <bk-button
              text
              @click="handleDelete($index)"
            >
              {{ $t('删除') }}
            </bk-button>
          </template>
        </template>
      </bk-table-column>
    </bk-table>
    <bk-button
      text
      size="small"
      @click="handleAdd"
    >
      <i class="paasng-icon paasng-plus-circle f14"></i>
      {{ $t('新增字段') }}
    </bk-button>
  </div>
</template>

<script>
export default {
  name: 'ConfigItemsTable',
  props: {
    value: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      // 字段类型列表
      fieldTypeList: [
        { id: 'string', name: 'string' },
        { id: 'integer', name: 'integer' },
        { id: 'boolean', name: 'boolean' },
      ],
      // 编辑前的备份数据
      editBackup: {},
      // 字段名校验规则
      keyRules: {
        key: [
          {
            required: true,
            message: this.$t('请输入字段名'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  methods: {
    // 校验方法（供父组件调用）
    async validate() {
      // 校验所有正在编辑中的行
      for (let index = 0; index < this.value.length; index++) {
        const item = this.value[index];
        if (item.isEditing) {
          const formRef = this.$refs[`keyForm${index}`];
          if (formRef) {
            await formRef.validate();
          }
        }
      }
    },
    // 新增配置项（默认为编辑态）
    handleAdd() {
      const newItem = {
        key: '',
        type: 'string',
        required: false,
        example: '',
        isEditing: true,
        isNew: true,
      };
      this.$emit('input', [...this.value, newItem]);
    },
    // 编辑配置项
    handleEdit(index) {
      const newValue = [...this.value];
      // 备份当前数据
      this.editBackup[index] = { ...newValue[index] };
      newValue[index] = { ...newValue[index], isEditing: true };
      this.$emit('input', newValue);
    },
    // 保存配置项
    async handleSave(index) {
      const formRef = this.$refs[`keyForm${index}`];
      // 表单校验
      try {
        await formRef.validate();
      } catch (e) {
        return;
      }
      const newValue = [...this.value];
      const item = newValue[index];
      newValue[index] = { ...item, isEditing: false, isNew: false };
      // 清除备份
      delete this.editBackup[index];
      this.$emit('input', newValue);
    },
    // 取消编辑
    handleCancel(index) {
      const newValue = [...this.value];
      const item = newValue[index];
      // 如果是新增的，直接删除
      if (item.isNew) {
        newValue.splice(index, 1);
      } else {
        // 恢复备份数据
        newValue[index] = { ...this.editBackup[index], isEditing: false };
        delete this.editBackup[index];
      }
      this.$emit('input', newValue);
    },
    // 删除配置项
    handleDelete(index) {
      const newValue = [...this.value];
      newValue.splice(index, 1);
      this.$emit('input', newValue);
    },
  },
};
</script>

<style lang="scss" scoped>
.config-items-table {
  /deep/ .bk-table-empty-block {
    min-height: 42px;
    height: 42px;
    border-bottom: 1px solid #e8e8e8;
  }
  /deep/ .bk-form-item {
    .bk-form-content {
      margin-left: 0 !important;
      display: flex;
      align-items: center;
    }
  }
}
</style>
