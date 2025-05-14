<template lang="html">
  <span>
    <slot name="trigger" />
    <slot name="content" />
  </span>
</template>

<script>
import Drop from 'tether-drop';

export default {
  // closeOnLinkClicked: If this is set to ture, when any link in content is clicked, dropdown
  //   will close.
  props: {
    options: {
      type: [Array, Object],
    },
    closeOnLinkClicked: {
      type: Boolean,
    },
    delay: {
      type: Number,
    },
  },
  data() {
    return {
      dropperOptions: this.options || {},
      instance: null,
    };
  },
  mounted() {
    if (!this.instance) {
      this.$emit('beforeInitialize');
      const self = this;
      this.instance = new Drop({
        target: this.$slots.trigger[0].elm,
        content: this.$slots.content[0].elm,
        classes: 'drop-theme-ps-arrow',
        openOn: 'click',
        beforeClose() {
          self.$emit('close');
        },
        ...this.dropperOptions,
      });

      this.instance.on('open', () => {
        this.$emit('open');
      });

      if (this.closeOnLinkClicked) {
        $(this.$slots.content[0].elm).on('click', 'a', (event) => {
          this.close();
        });
      }
    }
  },
  destroyed() {
    this.instance && this.instance.destroy();
    this.$emit('close');
  },
  methods: {
    close() {
      this.instance.close();
      this.$emit('close');
    },
    hide() {
      this.instance.toggle(false);
    },
    position() {
      this.instance.position();
    },
  },
};
</script>
