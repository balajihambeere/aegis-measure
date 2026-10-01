"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Label,
  Muted,
  PageHeader,
  SectionTitle,
  Select,
  Table,
  TableBody,
  TableHead,
  TextArea,
  TextInput,
} from "@/components/ui";
import { api, EvalRun, GoldenCase, Suite } from "@/lib/api";

const statusTone: Record<string, "pass" | "neutral" | "warn"> = {
  approved: "pass",
  draft: "neutral",
  needs_resolution: "warn",
  retired: "neutral",
};

const runStatusTone: Record<string, "pass" | "fail" | "neutral"> = {
  completed: "pass",
  errored: "fail",
  running: "neutral",
};

export default function SuiteDetailPage() {
  const { suiteId } = useParams<{ suiteId: string }>();
  const [suite, setSuite] = useState<Suite | null>(null);
  const [cases, setCases] = useState<GoldenCase[] | null>(null);
  const [runs, setRuns] = useState<EvalRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [question, setQuestion] = useState("");
  const [context, setContext] = useState("");
  const [source, setSource] = useState("manual");
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!suiteId) return;
    try {
      const [suite, cases, runs] = await Promise.all([
        api.getSuite(suiteId),
        api.listCases({ suite_id: suiteId }),
        api.listRuns(suiteId),
      ]);
      setSuite(suite);
      setCases(cases);
      setRuns(runs);
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [suiteId]);

  async function createCase(e: React.FormEvent) {
    e.preventDefault();
    if (!suiteId || !question.trim()) return;
    setBusy(true);
    try {
      await api.createCase({ suite_id: suiteId, question, context: context || undefined, source });
      setQuestion("");
      setContext("");
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!suite) return <Muted>Loading…</Muted>;

  return (
    <div>
      <PageHeader
        back={{ href: "/", label: "Suites" }}
        title={suite.name}
        description={suite.description || "No description."}
      />
      {error && <ErrorBanner>{error}</ErrorBanner>}

      <SectionTitle>Golden cases</SectionTitle>
      <Table>
        <TableHead columns={["Question", "Status", "Check mode", "Source"]} />
        <TableBody>
          {cases?.map((c) => (
            <tr key={c.id}>
              <td>{c.question}</td>
              <td>
                <Badge tone={statusTone[c.status]}>{c.status}</Badge>
              </td>
              <td className="text-muted">{c.check_mode}</td>
              <td className="text-muted">{c.source}</td>
            </tr>
          ))}
          {cases?.length === 0 && (
            <tr>
              <td colSpan={4} className="text-muted">
                No cases yet.
              </td>
            </tr>
          )}
        </TableBody>
      </Table>

      <SectionTitle>Add a draft case</SectionTitle>
      <Card className="max-w-lg">
        <form onSubmit={createCase}>
          <Label htmlFor="question">Question (verbatim, as actually asked)</Label>
          <TextInput id="question" value={question} onChange={(e) => setQuestion(e.target.value)} />
          <Label htmlFor="context">Context (the exact source material, optional)</Label>
          <TextArea id="context" rows={3} value={context} onChange={(e) => setContext(e.target.value)} />
          <Label htmlFor="source">Source</Label>
          <Select id="source" value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="real_complaint">real_complaint</option>
            <option value="support_queue">support_queue</option>
            <option value="manual_spotcheck">manual_spotcheck</option>
            <option value="manual">manual</option>
          </Select>
          <Button type="submit" disabled={busy} className="mt-4">
            Add draft case
          </Button>
        </form>
        <Muted className="mt-3 text-xs">
          New cases start as drafts — they need two independent reviews before they count toward a
          run. See the Review queue.
        </Muted>
      </Card>

      <SectionTitle>Runs</SectionTitle>
      {runs?.length === 0 ? (
        <EmptyState>No runs yet.</EmptyState>
      ) : (
        <Table>
          <TableHead columns={["Started", "Trigger", "Status"]} />
          <TableBody>
            {runs?.map((r) => (
              <tr key={r.id}>
                <td className="font-medium">
                  <Link className="text-accent hover:text-accent-hover hover:underline" href={`/runs/${r.id}`}>
                    {new Date(r.started_at).toLocaleString()}
                  </Link>
                </td>
                <td className="text-muted">{r.trigger_source}</td>
                <td>
                  <Badge tone={runStatusTone[r.status]}>{r.status}</Badge>
                </td>
              </tr>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
