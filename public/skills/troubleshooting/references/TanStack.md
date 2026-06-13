# TanStack Virtual + Vue 3: Anti-Patterns and Fixes

> Extracted from production implementation of `@tanstack/vue-virtual` with Vue 3 Composition API.

## The One Rule

Wrap the ENTIRE options object in `computed()`. Extract `scrollContainer.value` in the computed body (not just inside closures). This is non-negotiable.

```javascript
const virtualizerOptions = computed(() => {
  const scrollEl = scrollContainer.value; // Extract here so Vue tracks it
  return {
    count: data.value?.length || 0,           // Plain number, NOT computed()
    getScrollElement: () => scrollEl,
    estimateSize: () => estimateSize,
    overscan,
    scrollMargin: unref(scrollMargin),
  };
});
const rowVirtualizer = useVirtualizer(virtualizerOptions);
```

---

## Quick Diagnostic Checklist

| Symptom | Likely Cause | Section |
|---------|-------------|---------|
| `virtualTotalSize: 0`, no rows | Options not wrapped in `computed()`, or passing `ComputedRef` instead of number | 1.1, 1.2 |
| Rows don't update on data change | Plain object options (evaluated once) | 1.3 |
| Scroll container not detected after `v-if`/`v-else` | `scrollContainer.value` only accessed inside closure | 1.4 |
| `onScopeDispose()` warning | Virtualizer initialized inside lifecycle hook | 2.1 |
| `virtualItem.fileName` is undefined | Using virtualItem directly instead of `data[virtualItem.index]` | 4.1 |
| Rows overlap or wrong position | Missing absolute positioning or `translateY` | 5.1 |
| Rows offset when content above list | Missing `scrollMargin` option | 5.2 |
| Scroll container dimensions 0 | CSS missing explicit height or `overflow-y: auto` | 5.3 |

---

## 1. Options Configuration

### 1.1 Anti-Pattern: Individual Computed Properties

```javascript
// WRONG — passes ComputedRef instead of number
const rowVirtualizer = useVirtualizer({
  count: computed(() => data.value.length),  // Returns ComputedRef, not number!
  getScrollElement: () => scrollContainer.value,
  estimateSize: () => estimateSize
});
```

**Result:** `virtualTotalSize: 0`, no rows rendered, silent failure.

**Fix:** Wrap entire options in a single `computed()` (see The One Rule above).

### 1.2 Anti-Pattern: Nested Computed Inside Computed

Any individual property wrapped in `computed()` inside the options object produces a `ComputedRef` where TanStack expects a plain value.

**Fix:** All values inside the computed wrapper must resolve to plain types (`number`, `string`, `function`).

### 1.3 Anti-Pattern: Plain Object Without Reactivity

```javascript
// WRONG — evaluated once, never updates
const rowVirtualizer = useVirtualizer({
  count: data.value.length,  // Snapshot, not reactive
  getScrollElement: () => scrollContainer.value,
  estimateSize: () => estimateSize
});
```

**Result:** Works with initial data, doesn't update when `data.value` changes.

**Fix:** Wrap in `computed()`.

### 1.4 Anti-Pattern: scrollContainer.value Only in Closure

```javascript
// WRONG — Vue doesn't track scrollContainer.value inside the closure
const virtualizerOptions = computed(() => ({
  count: data.value?.length || 0,
  getScrollElement: () => scrollContainer.value,  // Not tracked!
  estimateSize: () => estimateSize,
}));
```

**Result:** Works when scroll container exists from the start. Fails with `v-if`/`v-else` patterns — TanStack never binds scroll listeners after the element appears.

**Fix:** Extract `scrollContainer.value` in the computed body:
```javascript
const virtualizerOptions = computed(() => {
  const scrollEl = scrollContainer.value; // Vue tracks this dependency
  return {
    count: data.value?.length || 0,
    getScrollElement: () => scrollEl,
    ...
  };
});
```

---

## 2. Initialization

### 2.1 Anti-Pattern: Lifecycle Hook Initialization

```javascript
// WRONG — causes "onScopeDispose() called when no active effect scope"
onMounted(async () => {
  const { virtualItems } = useVirtualTable({
    data: mockData,
    scrollContainer,
    estimateSize: 48
  });
});
```

**Why:** Vue composables use effect scopes for cleanup. These must be established during component setup, not in lifecycle hooks.

**Fix:** Initialize during setup, load data after:
```javascript
// During setup (synchronous, before any await)
const { virtualItems } = useVirtualTable({ data: mockData, scrollContainer, estimateSize: 48 });

// Data loads after mount — virtualizer reacts automatically
onMounted(async () => {
  mockData.value = await loadData();
});
```

### 2.2 Anti-Pattern: Manual Measure Calls

```javascript
// WRONG — unnecessary
onMounted(async () => {
  await nextTick();
  rowVirtualizer.value.measure(); // Not needed!
});
```

The virtualizer automatically measures when the scroll element becomes available. Null refs during setup are handled gracefully.

---

## 3. Data Access

### 3.1 Anti-Pattern: Direct Iteration on Virtual Items

```vue
<!-- WRONG — virtualItem is NOT your data object -->
<div v-for="virtualItem in virtualItems" :key="virtualItem.key">
  <span>{{ virtualItem.fileName }}</span>  <!-- undefined! -->
</div>
```

`virtualItems` contains TanStack metadata objects:
- `virtualItem.index` — Index in your data array
- `virtualItem.key` — Unique key for Vue
- `virtualItem.start` — Pixel offset for positioning
- `virtualItem.size` — Row height in pixels

**Fix:** Access data via index:
```vue
<div v-for="virtualItem in virtualItems" :key="virtualItem.key">
  <span>{{ data[virtualItem.index].fileName }}</span>
</div>
```

---

## 4. Template and CSS

### 4.1 Required Structure

```vue
<div ref="scrollContainer" style="height: 100vh; overflow-y: auto;">
  <div :style="{ height: virtualTotalSize + 'px', position: 'relative' }">
    <div
      v-for="virtualItem in virtualItems"
      :key="virtualItem.key"
      :style="{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: virtualItem.size + 'px',
        transform: `translateY(${virtualItem.start}px)`
      }"
    >
      {{ data[virtualItem.index].name }}
    </div>
  </div>
</div>
```

**Requirements:**
1. Scroll container: fixed height + `overflow-y: auto`
2. Virtual container: dynamic height from `virtualTotalSize`, `position: relative`
3. Virtual rows: `position: absolute` + `translateY(virtualItem.start)`

### 4.2 Anti-Pattern: Missing Scroll Container Height

**Symptom:** `scrollContainer dimensions: { width: 0, height: 0 }`

**Fix:** Scroll container must have an explicit height (`100vh`, `500px`, `calc(100vh - 64px)`, etc.) and `overflow-y: auto`.

### 4.3 scrollMargin for Offset Lists

**Symptom:** Rows render at wrong vertical positions when headers/tabs appear above the virtual list within the same scroll container.

**Fix:** Pass `scrollMargin`:
```javascript
useVirtualTable({
  data,
  scrollContainer,
  estimateSize: 48,
  scrollMargin: headerHeight  // Offset from scroll container top to virtual list start
});
```

---

## 5. Performance Baselines

| Metric | Expected |
|--------|----------|
| Initial render (1,000 rows) | <100ms |
| DOM nodes (viewport + overscan) | ~23 |
| DOM reduction vs static | ~43x |
| Scroll FPS | 60 |
| virtualTotalSize | count x estimateSize |

**Debug helpers** — `useVirtualTable` returns `virtualRange` and `scrollMetrics` built-in. No need to create your own.

---

## Key Takeaways

1. Always use the computed options wrapper pattern — non-negotiable
2. Extract `scrollContainer.value` in computed body — not just in closures
3. Initialize during setup scope — never in lifecycle hooks
4. Null refs are fine — TanStack handles them gracefully
5. Access data via `data[virtualItem.index]` — not `virtualItem.property`
6. Don't manually call `measure()` — trust the reactivity
7. Use `scrollMargin` when virtual list isn't at position 0 in scroll container
