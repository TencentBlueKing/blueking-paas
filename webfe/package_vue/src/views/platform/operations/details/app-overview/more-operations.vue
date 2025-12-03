<template>
  <div class="admin-operations">
    <div class="letf-btn">
      <slot></slot>
    </div>
    <dropdown
      ref="moreDropDown"
      :options="{ position: 'bottom right', openOn: 'hover', classes: 'drop-theme-ps-arrow admin-dropdown-cls' }"
      @open="handleDropdownOpen"
      @close="handleDropdownClose"
    >
      <bk-button
        slot="trigger"
        theme="primary"
        class="dropdown-trigger-cls"
      >
        <round-loading
          v-if="loading"
          theme="white"
        />
        <i
          v-else
          class="paasng-icon paasng-ps-arrow-down"
          :class="{ rotated: isDropdownOpen }"
        />
      </bk-button>
      <div slot="content">
        <ul class="ps-list-group-link spacing-x0">
          <li
            @click="handleItemClick"
            :class="{ disabled: disabled }"
          >
            <a>
              {{ $t('成为临时管理员，2小时后自动退出') }}
            </a>
          </li>
        </ul>
      </div>
    </dropdown>
  </div>
</template>

<script>
import dropdown from '@/components/ui/Dropdown';
export default {
  components: {
    dropdown,
  },
  props: {
    disabled: {
      type: Boolean,
      default: false,
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      isDropdownOpen: false,
    };
  },
  methods: {
    handleItemClick() {
      if (this.disabled || this.loading) return;
      this.$refs.moreDropDown.hide();
      this.$emit('dropdown-item-change');
    },
    handleDropdownOpen() {
      this.isDropdownOpen = true;
    },
    handleDropdownClose() {
      this.isDropdownOpen = false;
    },
  },
};
</script>

<style lang="scss">
.admin-dropdown-cls {
  .drop-content::after {
    display: none;
  }
  .ps-list-group-link {
    li.disabled a {
      color: #c4c6cc;
      cursor: not-allowed;
    }
  }
}
</style>
<style lang="scss" scoped>
.admin-operations {
  display: flex;
  align-items: center;
  gap: 1px;
  .letf-btn {
    overflow: hidden;
    /deep/ .bk-button {
      border-radius: 2px 0 0 2px;
    }
  }
  .dropdown-trigger-cls {
    width: 32px;
    min-width: 32px !important;
    border-radius: 0 2px 2px 0;
    padding: 0 !important;

    i {
      transition: transform 0.2s ease;
      &.rotated {
        transform: rotate(180deg) translateY(2px);
      }
    }
  }
}
</style>
