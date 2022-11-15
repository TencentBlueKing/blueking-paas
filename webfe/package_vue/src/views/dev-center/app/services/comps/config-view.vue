<template lang="html">
  <section>
    <h3 class="title">
      {{ $t('配置信息') }}
    </h3>
    <section class="content">
      <section
        v-for="(item, index) in listDisplay"
        :key="index"
        class="item"
        :class="index !== 0 ? 'set-top' : ''"
      >
        <label
          class="label"
          :title="item.name"
        >{{ item.name }}</label>
        <section class="value">
          {{ item.value }}
        </section>
      </section>
    </section>
    <section
      v-if="isEdit"
      class="action"
    >
      <bk-button
        :loading="saveLoading"
        @click="handleEdit"
      >
        {{ $t('修改配置信息') }}
      </bk-button>
    </section>
  </section>
</template>

<script>
    export default {
        name: '',
        props: {
            list: {
                type: Array,
                default: []
            },
            canEdit: {
                type: Boolean,
                default: true
            },
            loading: {
                type: Boolean,
                default: false
            }
        },
        data () {
            return {
                isEdit: this.canEdit,
                listDisplay: this.list,
                saveLoading: false
            };
        },
        watch: {
            list (value) {
                this.listDisplay = [...value];
            },
            canEdit (value) {
                this.isEdit = !!value;
            },
            loading (value) {
                this.saveLoading = !!value;
            }
        },
        methods: {
            handleEdit () {
                this.$emit('on-edit');
            }
        }
    };

</script>

<style lang="scss" scoped>
    .title {
        color: #1b1f23;
        font-weight: 600;
    }
    .content {
        padding-top: 15px;
        .item {
            position: relative;
            display: flex;
            justify-content: flex-start;
            line-height: 36px;
            border: 1px solid #dcdee5;
            &.set-top {
                margin-top: -1px;
            }
            .label {
                display: inline-block;
                padding: 0 10px;
                width: 115px;
                border-right: 1px solid #dcdee5;
                color: #313238;
                white-space: nowrap;
                text-overflow: ellipsis;
                overflow: hidden;
                vertical-align: middle;
            }
            .value {
                padding: 0 10px;
                width: 743px;
                white-space: nowrap;
                text-overflow: ellipsis;
                overflow: hidden;
            }
        }
    }
    .action {
        margin-top: 10px;
    }
</style>
