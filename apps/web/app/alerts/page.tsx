"use client";

import { useEffect, useState } from "react";
import { Badge, Button, EmptyState, ErrorBanner, PageHeader, Table, TableBody, TableHead } from "@/components/ui";
import { api, Alert } from "@/lib/api";

const typeLabel: Record<string, string> = {
  pass_rate_drop: "Pass rate drop",
  new_failure: "New failure",
  calibration_stale: "Calibration stale",
  coverage_gap_due: "Coverage gap overdue",
};

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [showAcknowledged, setShowAcknowledged] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setAlerts(await api.listAlerts({ unacknowledged_only: !showAcknowledged }));
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showAcknowledged]);

  async function acknowledge(id: string) {
    setBusy(true);
    try {
      await api.acknowledgeAlert(id);
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Alerts"
        description="Raised automatically when a run finds a new failure, a pass-rate drop, a stale judge calibration, or an overdue coverage re-review."
        action={
          <label className="inline-flex cursor-pointer items-center gap-2 text-sm font-medium text-muted">
            <input
              type="checkbox"
              className="h-4 w-4 cursor-pointer rounded border-border-strong bg-bg-raised text-accent accent-accent focus:outline-none focus:shadow-ring"
              checked={showAcknowledged}
              onChange={(e) => setShowAcknowledged(e.target.checked)}
            />
            Show acknowledged
          </label>
        }
      />
      {error && <ErrorBanner>{error}</ErrorBanner>}

      {alerts?.length === 0 ? (
        <EmptyState>Nothing to see here.</EmptyState>
      ) : (
        <Table>
          <TableHead columns={["Type", "Message", "Raised", ""]} />
          <TableBody>
            {alerts?.map((a) => (
              <tr key={a.id}>
                <td>
                  <Badge tone="warn">{typeLabel[a.alert_type]}</Badge>
                </td>
                <td>{a.message}</td>
                <td className="text-muted">{new Date(a.created_at).toLocaleString()}</td>
                <td>
                  {!a.acknowledged_at && (
                    <Button variant="secondary" disabled={busy} onClick={() => acknowledge(a.id)}>
                      Acknowledge
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
