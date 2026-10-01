"use client";

import { useEffect, useState } from "react";
import { Badge, Card, EmptyState, ErrorBanner, Muted, PageHeader, Table, TableBody, TableHead } from "@/components/ui";
import { api, CalibrationRun, Rubric } from "@/lib/api";

export default function CalibrationPage() {
  const [rubrics, setRubrics] = useState<Rubric[] | null>(null);
  const [runsByRubric, setRunsByRubric] = useState<Record<string, CalibrationRun[]>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const rubrics = await api.listRubrics();
        setRubrics(rubrics);
        const entries = await Promise.all(
          rubrics.map(async (r) => [r.id, await api.listCalibrationRuns(r.id)] as const),
        );
        setRunsByRubric(Object.fromEntries(entries));
      } catch (e) {
        setError(String(e));
      }
    })();
  }, []);

  return (
    <div>
      <PageHeader
        title="Judge calibration"
        description="A judge's verdicts are only trustworthy once they're checked against human verdicts on known cases — re-run whenever the golden set gains a new category or the judge model changes."
      />
      {error && <ErrorBanner>{error}</ErrorBanner>}

      {rubrics?.map((rubric) => {
        const runs = runsByRubric[rubric.id] ?? [];
        const latest = runs[0];
        return (
          <Card key={rubric.id}>
            <div className="flex items-center justify-between gap-4">
              <strong className="text-[0.95rem] font-semibold text-ink">{rubric.name}</strong>
              {latest ? (
                <Badge tone={latest.passed_threshold ? "pass" : "fail"}>
                  {(latest.agreement_rate * 100).toFixed(0)}% agreement ({latest.judge_model_version})
                </Badge>
              ) : (
                <Badge tone="neutral">never calibrated</Badge>
              )}
            </div>
            <Muted className="mt-1 text-xs">
              Dimensions: {rubric.dimensions.map((d) => d.key).join(", ")}
            </Muted>
            {runs.length > 0 && (
              <Table>
                <TableHead columns={["Judge model", "Agreement", "Sample size", "Run at"]} />
                <TableBody>
                  {runs.map((run) => (
                    <tr key={run.id}>
                      <td className="font-medium">{run.judge_model_version}</td>
                      <td>
                        <Badge tone={run.passed_threshold ? "pass" : "fail"}>
                          {run.agreement_count}/{run.sample_size}
                        </Badge>
                      </td>
                      <td className="text-muted">{run.sample_size}</td>
                      <td className="text-muted">{new Date(run.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </TableBody>
              </Table>
            )}
          </Card>
        );
      })}
      {rubrics?.length === 0 && <EmptyState>No rubrics defined yet.</EmptyState>}
    </div>
  );
}
