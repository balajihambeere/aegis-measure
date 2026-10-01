"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PlayIcon } from "@/components/icons";
import {
  Badge,
  Button,
  Card,
  ErrorBanner,
  Label,
  PageHeader,
  SectionTitle,
  StatCard,
  StatGrid,
  Table,
  TableBody,
  TableHead,
  TextInput,
} from "@/components/ui";
import { api, EvalRun, Suite } from "@/lib/api";

interface SuiteRow {
  suite: Suite;
  latestRun: EvalRun | null;
  passCount: number;
  totalCount: number;
}

export default function SuitesPage() {
  const [rows, setRows] = useState<SuiteRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const suites = await api.listSuites();
      const rows = await Promise.all(
        suites.map(async (suite) => {
          const runs = await api.listRuns(suite.id);
          const latestRun = runs[0] ?? null;
          if (!latestRun) return { suite, latestRun: null, passCount: 0, totalCount: 0 };
          const results = await api.getRunResults(latestRun.id);
          return {
            suite,
            latestRun,
            passCount: results.filter((r) => r.passed).length,
            totalCount: results.length,
          };
        }),
      );
      setRows(rows);
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function createSuite(e: React.FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setBusy(true);
    try {
      await api.createSuite({ name: newName.trim() });
      setNewName("");
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function triggerRun(suiteId: string) {
    setBusy(true);
    try {
      await api.triggerRun(suiteId);
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const withResults = rows?.filter((r) => r.totalCount > 0) ?? [];
  const healthy = withResults.filter((r) => r.passCount === r.totalCount).length;
  const needsAttention = withResults.length - healthy;
  const avgPassRate = withResults.length
    ? Math.round(
        (withResults.reduce((sum, r) => sum + r.passCount / r.totalCount, 0) / withResults.length) * 100,
      )
    : null;

  return (
    <div>
      <PageHeader
        title="Suites"
        description="Each suite's latest run pass rate — a checked, reproducible number instead of a guess about whether the system is still working."
      />

      {error && <ErrorBanner>{error}</ErrorBanner>}

      {rows && rows.length > 0 && (
        <StatGrid>
          <StatCard label="Total suites" value={rows.length} />
          <StatCard label="Healthy" value={healthy} tone="pass" />
          <StatCard label="Needs attention" value={needsAttention} tone={needsAttention > 0 ? "fail" : "neutral"} />
          <StatCard
            label="Avg pass rate"
            value={avgPassRate === null ? "—" : `${avgPassRate}%`}
            tone={avgPassRate === null ? "neutral" : avgPassRate === 100 ? "pass" : "warn"}
          />
        </StatGrid>
      )}

      <Table>
        <TableHead columns={["Suite", "Last run", "Pass rate", "Trigger", "Interval", ""]} />
        <TableBody>
          {rows?.map(({ suite, latestRun, passCount, totalCount }) => (
            <tr key={suite.id}>
              <td className="font-medium">
                <Link className="text-accent hover:text-accent-hover hover:underline" href={`/suites/${suite.id}`}>
                  {suite.name}
                </Link>
              </td>
              <td className="text-muted">
                {latestRun ? new Date(latestRun.started_at).toLocaleString() : "never run"}
              </td>
              <td>
                {totalCount > 0 ? (
                  <Badge tone={passCount === totalCount ? "pass" : "fail"}>
                    {passCount}/{totalCount}
                  </Badge>
                ) : (
                  <Badge tone="neutral">no results</Badge>
                )}
              </td>
              <td className="text-muted">{latestRun?.trigger_source}</td>
              <td className="text-muted">{suite.default_schedule_interval_hours}h</td>
              <td>
                <Button variant="secondary" disabled={busy} onClick={() => triggerRun(suite.id)}>
                  <PlayIcon className="h-3.5 w-3.5" />
                  Run now
                </Button>
              </td>
            </tr>
          ))}
        </TableBody>
      </Table>

      <SectionTitle>New suite</SectionTitle>
      <Card className="max-w-sm">
        <form onSubmit={createSuite}>
          <Label htmlFor="suite-name">Name</Label>
          <TextInput
            id="suite-name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="e.g. fabric-and-care"
          />
          <Button type="submit" disabled={busy} className="mt-4">
            Create suite
          </Button>
        </form>
      </Card>
    </div>
  );
}
