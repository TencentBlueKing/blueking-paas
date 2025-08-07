<template>
  <div class="flex-row align-items-center justify-content-between">
    <div>
      <span v-if="type === 'tc_git'">{{ $t('首次使用工蜂，请先阅读') }}</span>
      <a
        :href="data?.authDocs"
        target="_blank"
      >
        {{ $t('授权指引文档') }}
      </a>
    </div>
    <span>
      <a
        style="cursor: pointer"
        @click="authAssociate(data?.authAddress, data?.fetchMethod)"
      >
        {{ $t('已阅读') }}? {{ $t('去关联') }}
      </a>
    </span>
  </div>
</template>

<script>
export default {
  props: {
    type: {
      type: String,
      default: 'tc_git',
    },
    data: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {};
  },
  methods: {
    // 关联授权
    authAssociate(authUrl, callback) {
      this.check_window_close(
        window.open(
          authUrl,
          this.$t('授权窗口'),
          'height=600, width=600, top=200, left=400, toolbar=no, menubar=no, scrollbars=no, resizable=no, location=no, status=no'
        ),
        300,
        callback
      );
    },
  },
};
</script>
