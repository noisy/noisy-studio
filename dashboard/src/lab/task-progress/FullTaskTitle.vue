<script setup lang="ts">
defineProps<{ text: string }>();
</script>
<template>
  <span class="full-task-title" tabindex="0" :aria-label="text"
    ><span class="truncated">{{ text }}</span
    ><span class="full-text" aria-hidden="true">{{ text }}</span></span
  >
</template>
<style scoped>
.full-task-title {
  position: relative;
  display: block;
  min-width: 0;
  font-size: 9px;
  line-height: 16px;
  outline-offset: 2px;
}
.truncated {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.full-text {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 10;
  width: 210px;
  max-width: calc(100vw - 60px);
  padding: 7px 9px;
  border: 1px solid #65778d;
  border-radius: 5px;
  background: #242e3c;
  color: #e4e7ee;
  white-space: normal;
  line-height: 1.5;
  box-shadow: 0 5px 15px #0005;
  pointer-events: none;
}
.full-task-title:hover .full-text,
.full-task-title:focus .full-text {
  display: block;
}
</style>
