// frontend/src/components/primitives/slice-detail-view.tsx
import { useReportSla } from "#/hooks/use-reportsla";
import { useSliceViewModel } from "#/hooks/use-slice-view-model";
import type { SliceSharedProps } from "#/types/slice-shared";
import type { SliceViewConfig } from "#/types/slice-view-config";
import { PanelFrame } from "./panel-frame";
import { RecentCyclesPanel } from "./slice-dashboard/recent-cycles-panel";
import { SliceChart } from "./slice-dashboard/slice-chart";
import { SliceLayout } from "./slice-layout";

export function SliceDetailView({
  config,
  switcherTabs,
  activeSlice,
  onSliceChange,
  onSlaChange,
}: { config: SliceViewConfig } & SliceSharedProps) {
  const { chartData, header, right, historyRows } = useSliceViewModel(config);
  useReportSla(header.slaMet ?? false, onSlaChange);

  return (
    <SliceLayout
      switcherTabs={switcherTabs}
      activeSlice={activeSlice}
      onSliceChange={onSliceChange}
      telemetryLabel={config.telemetryLabel ?? "Telemetry Timeline"}
      header={header}
      right={right}
      history={{
        rows: historyRows,
        title: `${config.name} History`,
        thrptHeader: config.thrptHeader,
      }}
    >
      {config.charts.map((spec) => (
        <SliceChart key={spec.dataKey + spec.title} spec={spec} data={chartData} />
      ))}
      <PanelFrame title="Recent Cycles" motif={false}>
        <RecentCyclesPanel cycles={right.recentCycles} cols={right.recentCols} />
      </PanelFrame>
    </SliceLayout>
  );
}
