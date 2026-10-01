"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AnswerBlock, Badge, Card, EmptyState, ErrorBanner, Label, Muted, PageHeader, Table, TableBody } from "@/components/ui";
import { api, CaseResult, EvalRun, GoldenCase } from "@/lib/api";

const diagnosisLabel: Record<string, string> = {
  upstream_retrieval_fault: "Upstream / retrieval fault",
  reasoning_fault: "Reasoning fault",
  none: "",
};

export default function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<EvalRun | null>(null);
  const [results, setResults] = useState<CaseResult[] | null>(null);
  const [cases, setCases] = useState<Record<string, GoldenCase>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    (async () => {
      try {
        const [run, results] = await Promise.all([api.getRun(runId), api.getRunResults(runId)]);
        setRun(run);
        setResults(results);
        const uniqueCaseIds = [...new Set(results.map((r) => r.case_id))];
        const fetched = await Promise.all(uniqueCaseIds.map((id) => api.getCase(id)));
        setCases(Object.fromEntries(fetched.map((c) => [c.id, c])));
      } catch (e) {
        setError(String(e));
      }
    })();
  }, [runId]);

  if (!run) return <Muted>Loading…</Muted>;

  return (
    <div>
      <PageHeader
        back={{ href: `/suites/${run.suite_id}`, label: "Suite" }}
        title={`Run ${new Date(run.started_at).toLocaleString()}`}
        description={
          <>
            Trigger: {run.trigger_source} · Judge: {run.judge_model_version} · Status: {run.status}
          </>
        }
      />
      {error && <ErrorBanner>{error}</ErrorBanner>}

      {results?.map((r) => {
        const c = cases[r.case_id];
        return (
          <Card key={r.id}>
            <div className="flex items-center justify-between gap-4">
              <strong className="text-[0.95rem] font-semibold text-ink">{c?.question ?? r.case_id}</strong>
              <div className="flex shrink-0 items-center gap-2">
                <Badge tone={r.passed ? "pass" : "fail"}>
                  {r.check_mode} · {r.passed ? "PASS" : "FAIL"}
                </Badge>
                {r.diagnosis !== "none" && <Badge tone="warn">{diagnosisLabel[r.diagnosis]}</Badge>}
              </div>
            </div>

            <Label>Candidate answer</Label>
            <AnswerBlock>{r.candidate_answer || "(no answer — see rationale below)"}</AnswerBlock>

            {c?.reference_answer && (
              <>
                <Label>Reference answer</Label>
                <AnswerBlock>{c.reference_answer}</AnswerBlock>
              </>
            )}

            {r.retrieved_context && (
              <>
                <Label>Context used (frozen for component checks, retrieved for end-to-end)</Label>
                <AnswerBlock>{r.retrieved_context}</AnswerBlock>
              </>
            )}

            <Label>Rubric dimensions</Label>
            <Table>
              <TableBody>
                {Object.entries(r.dimension_results).map(([key, dim]) => (
                  <tr key={key}>
                    <td className="w-2/5 font-medium">{key}</td>
                    <td>
                      <Badge tone={dim.passed ? "pass" : "fail"}>{dim.passed ? "pass" : "fail"}</Badge>
                    </td>
                    <td className="text-muted">{dim.rationale}</td>
                  </tr>
                ))}
              </TableBody>
            </Table>
          </Card>
        );
      })}
      {results?.length === 0 && <EmptyState>No approved cases ran in this suite yet.</EmptyState>}
    </div>
  );
}
