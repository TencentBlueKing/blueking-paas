export default {
  data() {
    return {
      mixinTargetBuildpackIds: null,
    };
  },
  methods: {
    /**
     * 开启拖拽功能
     * @param {*} className
     */
    mixinSetDraggableProp(className) {
      const itemElements = document.querySelectorAll(className);
      for (let i = 0; i < itemElements.length; i++) {
        itemElements[i].draggable = true;
      }
    },

    /**
     * 拖拽事件绑定
     * @param {*} listEl 需要绑定拖拽的元素列表
     * @param {*} listClassName
     */
    mixinBindDragEvent(listEl, listClassName) {
      if (!listEl) {
        return;
      }

      // 当前拖拽元素
      let sourceNode = null;

      // 拖拽开始
      listEl.ondragstart = (e) => {
        const target = e.target.closest(listClassName); // 确保获取到正确的列表项
        if (target) {
          setTimeout(() => {
            target.classList.add('moving');
          }, 0);
          sourceNode = target;
          if (e.dataTransfer) {
            e.dataTransfer.effectAllowed = 'move';
          }
        }
      };

      listEl.ondragenter = (e) => {
        // 确保获取到正确的列表项
        const targetNode = e.target.closest(listClassName);
        if (!targetNode || targetNode === sourceNode) {
          return;
        }
        const children = Array.from(listEl.children);
        const sourceIndex = children.indexOf(sourceNode);
        const targetIndex = children.indexOf(targetNode);

        // 确保 sourceNode 和 targetNode 都是 listEl 的直接子节点
        if (sourceIndex !== -1 && targetIndex !== -1) {
          if (sourceIndex < targetIndex) {
            // 向下
            listEl.insertBefore(sourceNode, targetNode.nextElementSibling);
          } else {
            // 向上
            listEl.insertBefore(sourceNode, targetNode);
          }
        }
      };

      listEl.ondragover = (e) => {
        e.preventDefault();
      };

      listEl.ondragend = (e) => {
        const target = e.target.closest(listClassName); // 确保获取到正确的列表项
        if (target) {
          target.classList.remove('moving');
        }
        // 列表元素
        const liElements = document.querySelectorAll(listClassName);
        const sourceIds = [];
        for (let i = 0; i < liElements.length; i++) {
          const childrenDiv = liElements[i].children[0];
          const id = childrenDiv.getAttribute('data-id');
          if (id) {
            const numberValue = Number(id);
            sourceIds.push(isNaN(numberValue) ? id : numberValue);
          }
        }
        this.mixinTargetBuildpackIds = sourceIds;
      };
    },
  },
};
