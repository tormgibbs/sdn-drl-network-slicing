import { useEffect } from "react";

export function useReportSla(slaMet: boolean, onSlaChange: (ok: boolean) => void) {
  useEffect(() => {
    onSlaChange(slaMet);
  }, [slaMet, onSlaChange]);
}