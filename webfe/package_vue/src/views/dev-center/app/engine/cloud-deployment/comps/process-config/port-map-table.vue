<template>
  <div>
    <bk-table
      :data="portMapList"
      ext-cls="port-map-table-cls"
    >
      <bk-table-column
        :label="$t('端口名称')"
        prop="name"
        show-overflow-tooltip
      >
        <template slot-scope="{ row, $index }">
          <div v-if="row.isEdit">
            <editable-cell
              v-if="row.isEdit"
              :ref="`name${$index}`"
              :row="row"
              :index="$index"
              prop="name"
              :rules="rules"
            />
          </div>
          <div v-else>
            {{ row.name }}
            <span
              v-if="row.exposed_type?.name"
              class="tag"
              v-bk-tooltips="{
                content: $t('每个模块可以设置一个访问入口，请求访问地址时{t}会被转发到访问入口指向的目标服务上。', {
                  t: address ? `（${$t('如：')}${address}）` : '',
                }),
                width: 260,
                placement: 'bottom',
              }"
            >
              {{ `${$t('访问入口')}（${row.exposed_type?.name === 'bk/http' ? 'HTTP' : 'gRPC'}）` }}
            </span>
          </div>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="$t('协议')"
        prop="protocol"
      >
        <template slot-scope="{ row, $index }">
          <div v-if="row.isEdit">
            <!-- 下拉框 -->
            <editable-cell
              v-if="row.isEdit"
              type="select"
              :ref="`protocol${$index}`"
              :row="row"
              :index="$index"
              prop="protocol"
              :rules="rules"
              :list="options"
            />
          </div>
          <div v-else>{{ row.protocol }}</div>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="`${$t('服务端口')}（Port）`"
        prop="port"
      >
        <template slot-scope="{ row, $index }">
          <editable-cell
            v-if="row.isEdit"
            :ref="`port${$index}`"
            :row="row"
            :index="$index"
            prop="port"
            :rules="rules"
          />
          <div v-else>{{ row.port }}</div>
        </template>
      </bk-table-column>
      <bk-table-column
        :label="`${$t('容器端口')}（TargetPort）`"
        prop="target_port"
      >
        <template slot-scope="{ row, $index }">
          <div v-if="row.isEdit">
            <editable-cell
              v-if="row.isEdit"
              :ref="`targetPort${$index}`"
              :row="row"
              :index="$index"
              prop="target_port"
              :rules="rules"
            />
          </div>
          <div v-else>{{ row.target_port }}</div>
        </template>
      </bk-table-column>
      <bk-table-column
        v-if="editMode"
        :label="$t('操作')"
        :width="localLanguage === 'en' ? 240 : 200"
      >
        <template slot-scope="{ row, $index }">
          <template v-if="!row.isEdit">
            <bk-button
              theme="primary"
              class="mr10"
              text
              @click="handlePortEdit(row)"
            >
              {{ $t('编辑') }}
            </bk-button>
            <!-- 最后一条不能删除 -->
            <bk-button
              theme="primary"
              text
              :disabled="portMapList.filter((v) => !v.isAdd).length === 1"
              @click="handleDelete(row)"
            >
              {{ $t('删除') }}
            </bk-button>
          </template>
          <template v-else>
            <bk-button
              theme="primary"
              class="mr10"
              text
              @click="handleConfirm(row, $index)"
            >
              {{ $t('确定') }}
            </bk-button>
            <bk-button
              theme="primary"
              text
              @click="handleCancel(row)"
            >
              {{ $t('取消') }}
            </bk-button>
          </template>
          <template v-if="!row.isAdd">
            <bk-button
              v-if="row.exposed_type?.name"
              theme="primary"
              class="ml10"
              text
              :disabled="row.isEdit"
              @click="setAccessEntryPoint(row, 'cancel')"
            >
              {{ $t('取消访问入口') }}
            </bk-button>
            <bk-popconfirm
              v-else
              width="360"
              trigger="click"
              placement="bottom-end"
              @confirm="setAccessEntryPoint(row, 'set')"
            >
              <div
                slot="content"
                class="popconfirm-content-cls"
              >
                <p class="popconfirm-title">{{ $t('确定设为访问入口？') }}</p>
                <div class="content-cls">
                  <span class="label">{{ $t('访问协议') }}</span>
                  <bk-radio-group v-model="accessEntryType">
                    <bk-radio
                      :value="'bk/http'"
                      class="f12"
                    >
                      HTTP
                    </bk-radio>
                    <bk-radio
                      :value="'bk/grpc'"
                      class="f12"
                    >
                      gRPC
                    </bk-radio>
                  </bk-radio-group>
                </div>
                <p class="access-entry-tip">{{ accessEntryTip }}</p>
              </div>
              <span
                v-bk-tooltips="{ content: $t('仅 TCP 协议的端口才能设置为访问入口'), disabled: row.protocol !== 'UDP' }"
              >
                <bk-button
                  theme="primary"
                  class="ml10"
                  text
                  :disabled="row.protocol === 'UDP' || row.isEdit"
                >
                  {{ $t('设为访问入口') }}
                </bk-button>
              </span>
            </bk-popconfirm>
          </template>
        </template>
      </bk-table-column>
      <!-- 新建环境变量 -->
      <template
        slot="append"
        v-if="editMode"
      >
        <div class="append-wrapper">
          <span
            class="add-port"
            @click.self="addPortMapping()"
          >
            <i class="paasng-icon paasng-plus-thick" />
            {{ $t('新增端口映射') }}
          </span>
        </div>
      </template>
    </bk-table>
  </div>
</template>

<script>
import editableCell from './editable-cell.vue';
import { cloneDeep } from 'lodash';
export default {
  name: 'PordMapTable',
  components: {
    editableCell,
  },
  props: {
    mode: {
      type: String,
      default: 'edit',
    },
    name: {
      type: String,
      default: '',
    },
    address: {
      type: String,
      default: '',
    },
    services: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      portMapList: [],
      oldRowsData: {},
      options: [{ name: 'TCP' }, { name: 'UDP' }],
      curProcessServie: {},
      dialogCofig: {
        visiable: false,
        type: 'set',
      },
      accessEntryType: 'bk/http',
      rules: {
        name: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
          {
            validator: (val) => {
              const list = this.portMapList.filter((v) => String(v.name) === String(val));
              return list.length < 2;
            },
            message: this.$t('服务名称不允许重复'),
            trigger: 'blur',
          },
        ],
        protocol: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
        port: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
          {
            validator: (val) => {
              const list = this.portMapList.filter((v) => String(v.port) === String(val));
              return list.length < 2;
            },
            message: this.$t('服务端口不允许重复'),
            trigger: 'blur',
          },
          {
            validator: (val) => this.isValidPort(val),
            message: this.$t('1~65535 或者 $PORT'),
            trigger: 'blur',
          },
        ],
        target_port: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
          {
            validator: (val) => {
              const list = this.portMapList.filter((v) => String(v.target_port) === String(val));
              return list.length < 2;
            },
            message: this.$t('容器端口不允许重复'),
            trigger: 'blur',
          },
          {
            validator: (val) => this.isValidPort(val),
            message: this.$t('1~65535 或者 $PORT'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    editMode() {
      return this.mode === 'edit';
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    accessEntryTip() {
      return this.accessEntryType === 'bk/http'
        ? this.$t('适用于外部 API 提供，适合 Web 和移动应用')
        : this.$t('适用于高性能、实时、内部服务通信');
    },
  },
  watch: {
    services: {
      handler(newValues) {
        this.portMapList = newValues.map((item) => ({
          ...item,
          id: this.generateId(),
          isEdit: false,
        }));
      },
      deep: true,
      immediate: true,
    },
  },
  methods: {
    isValidPort(input) {
      if (input === '$PORT') return true;
      const portNumber = Number(input);
      // 检查是否是整数，并且在范围 1 到 65535 之间
      if (Number.isInteger(portNumber) && portNumber >= 1 && portNumber <= 65535) return true;
      return false;
    },
    // 生成唯一ID
    generateId() {
      return `${Date.now()}-${Math.floor(Math.random() * 10000)}`;
    },
    // 编辑端口映射
    handlePortEdit(row) {
      if (!this.oldRowsData[row.id]) {
        this.oldRowsData[row.id] = cloneDeep(row);
      }
      this.portMapList.forEach((v) => {
        v.isEdit = false;
      });
      // 只允许单挑编辑
      row.isEdit = true;
    },
    // 确定
    handleConfirm(row, i) {
      Promise.all([
        this.$refs[`name${i}`].validate(),
        this.$refs[`protocol${i}`].validate(),
        this.$refs[`port${i}`].validate(),
        this.$refs[`targetPort${i}`].validate(),
      ])
        .then(() => {
          if (this.oldRowsData[row.id]) {
            delete this.oldRowsData[row.id];
          }
          this.$emit('change-service', {
            name: this.name,
            type: row.isAdd ? 'add' : 'edit',
            editIndex: i,
            service: row,
          });
          delete row.isAdd;
          row.isEdit = false;
        })
        .catch((e) => {
          console.error(e);
        });
    },
    // 取消复原数据
    handleCancel(row) {
      if (row.isAdd) {
        this.replacePortMapItem(row.name);
        return;
      }
      // 改动name无法获取的缓存数据
      this.replacePortMapItem(row.name, this.oldRowsData[row.id]);
    },
    handleDelete(row) {
      this.replacePortMapItem(row.name);
      this.$emit('delete-service', row.name);
    },
    // 新增端口映射
    addPortMapping() {
      this.portMapList.push({
        id: this.generateId(),
        name: '',
        protocol: 'TCP',
        port: '',
        target_port: '',
        isEdit: true,
        isAdd: true,
      });
    },
    replacePortMapItem(name, newItem) {
      const index = this.portMapList.findIndex((item) => item.name === name);
      if (index !== -1) {
        // 同步到父组件
        if (newItem) {
          // 替换数据
          this.portMapList.splice(index, 1, { ...newItem });
        } else {
          this.portMapList.splice(index, 1);
        }
      }
    },
    async formValidate(i) {
      await this.$refs[`name${i}`].validate();
      await this.$refs[`protocol${i}`].validate();
    },
    // 设为访问入口
    setAccessEntryPoint(row, type) {
      this.$emit('change-access-entry', {
        name: this.name,
        type,
        row,
        exposedType: this.accessEntryType,
      });
      this.resetExposedType();
    },
    resetExposedType() {
      this.$nextTick(() => {
        this.accessEntryType = 'bk/http';
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.port-map-table-cls {
  .append-wrapper {
    height: 42px;
    .add-port {
      display: inline-block;
      height: 42px;
      line-height: 42px;
      padding: 0 15px;
      color: #3a84ff;
      cursor: pointer;
      i {
        font-size: 16px;
        transform: translateY(0px);
      }
    }
  }
  .tag {
    display: inline-block;
    height: 22px;
    line-height: 22px;
    padding: 0 8px;
    font-size: 12px;
    color: #3a84ff;
    background: #eef4fe;
    border-radius: 2px;
    margin-left: 5px;
  }
}
.main-dialog-cls {
  .dialog-content {
    .item {
      display: flex;
      align-items: center;
      margin-bottom: 16px;
      .label {
        color: #63656e;
      }
    }
  }
  .alert-content {
    display: flex;
    .paasng-remind {
      transform: translateY(0px);
      margin-right: 8px;
      font-size: 14px;
      color: #ff9c01;
      line-height: 20px;
    }
    .tips p {
      line-height: 20px;
    }
  }
}
.popconfirm-content-cls {
  margin-bottom: 16px;
  .popconfirm-title {
    font-weight: 400;
    font-size: 16px;
    color: #313238;
    line-height: 24px;
  }
  .content-cls {
    display: flex;
    align-items: center;
    margin: 12px 0 8px 0;
    font-size: 12px;
    line-height: 20px;
    .label {
      position: relative;
      flex-shrink: 0;
      width: 64px;
      color: #4d4f56;
      &::after {
        content: '*';
        position: absolute;
        top: 50%;
        height: 8px;
        line-height: 1;
        color: #ea3636;
        font-size: 12px;
        transform: translate(3px, -50%);
      }
    }
  }
  .access-entry-tip {
    color: #979ba5;
    margin-left: 64px;
  }
}
</style>
