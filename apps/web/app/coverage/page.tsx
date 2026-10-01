"use client";

import { useEffect, useState } from "react";
import { Badge, Button, Card, EmptyState, ErrorBanner, Label, Muted, PageHeader, Tone } from "@/components/ui";
import { api, LaunchCoverageCheck } from "@/lib/api";

const statusTone: Record<string, Tone> = {
  covered: "pass",
  partial: "warn",
  none: "fail",
};

export default function CoveragePage() {
  const [checks, setChecks] = useState<LaunchCoverageCheck[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setChecks(await api.listCoverageChecks());
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function completeReReview(id: string) {
    setBusy(true);
    try {
      await api.completeReReview(id);
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
        title="Coverage gate"
        description={
          <>&quot;If this broke silently, who would notice, and when?&quot; — every launch&apos;s
          answer, written down, with any gaps named on purpose instead of discovered by accident.</>
        }
      />
      {error && <ErrorBanner>{error}</ErrorBanner>}

      {checks?.map((check) => (
        <Card key={check.id}>
          <div className="flex items-center justify-between gap-4">
            <strong className="text-[0.95rem] font-semibold text-ink">{check.feature_name}</strong>
            <Badge tone={statusTone[check.coverage_status]}>{check.coverage_status}</Badge>
          </div>
          <Muted className="mt-1 text-xs">
            Launched {check.launch_date} · answered by {check.answered_by}
          </Muted>
          {check.declared_gaps.length > 0 && (
            <>
              <Label>Declared gaps</Label>
              <ul className="list-disc space-y-0.5 pl-5 text-sm text-ink/90">
                {check.declared_gaps.map((gap, i) => (
                  <li key={i}>{gap}</li>
                ))}
              </ul>
            </>
          )}
          {check.re_review_due_at && (
            <p className="mt-4 flex items-center gap-2 text-sm">
              Re-review due {check.re_review_due_at} —{" "}
              {check.re_review_completed_at ? (
                <Badge tone="pass">completed</Badge>
              ) : (
                <Button variant="secondary" disabled={busy} onClick={() => completeReReview(check.id)}>
                  Mark re-review complete
                </Button>
              )}
            </p>
          )}
        </Card>
      ))}
      {checks?.length === 0 && <EmptyState>No launches registered yet.</EmptyState>}
    </div>
  );
}
