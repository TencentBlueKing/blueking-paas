<template lang="html">
  <!-- loading true时显示loading -->
  <div class="paas-loading-content">
    <slot v-if="loading">
      <div class="paas-loading-panel">
        <div class="text">
          <div class="bk-loading1">
            <div class="point point1" />
            <div class="point point2" />
            <div class="point point3" />
            <div class="point point4" />
          </div>
        </div>
      </div>
    </slot>
    <slot
      v-else
      name="loadingContent"
    />
  </div>
</template>

<script>

    export default {
        props: {
            loading: {
                type: Boolean
            }
        }
    };
</script>

<style lang="scss">

</style>
