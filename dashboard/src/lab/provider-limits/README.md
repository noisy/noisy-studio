# Provider limits · three compact dashboard designs

Exactly three Lab stories: Thin Bars, Bold Bars, Three Columns. All render the actual App.vue with the existing synthetic conversation fixture. The wrapper inserts a lab-only Teleport target before Session usage in the real 268px left rail, then removes its targets on unmount. No production UI changes, live daemon access, account credentials, or provider APIs.

Each summary has a compact title, Details action, and Session / Weekly / Opus weekly progress bars. Percentages mean USED. Account icons and account labels are deliberately omitted. Tooltips identify reset times and account-wide scope. Defaults use amber at 70% and red at 90% in these fixtures.

Details opens a separate Usage center pane and Back restores the conversation. The history graph uses synthetic regular five-minute samples, leaves collection gaps empty, and breaks at reset boundaries. A weekly quota window is shown over the same short observation interval; the chart is not a full week. Attribution remains unavailable because account deltas cannot prove per-thread consumption.

Earlier standalone account panels and mock dashboards have been removed, including their story IDs. This remains design-only pending user selection.
