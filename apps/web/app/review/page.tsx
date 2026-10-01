"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge, EmptyState, ErrorBanner, PageHeader, Table, TableBody, TableHead } from "@/components/ui";
import { api, GoldenCase, Suite } from "@/lib/api";

export default function ReviewQueuePage() {
  const [cases, setCases] = useState<GoldenCase[] | null>(null);
  const [suites, setSuites] = useState<Record<string, Suite>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [draft, needsResolution, suiteList] = await Promise.all([
          api.listCases({ status: "draft" }),
          api.listCases({ status: "needs_resolution" }),
          api.listSuites(),
        ]);
        setCases([...needsResolution, ...draft]);
        setSuites(Object.fromEntries(suiteList.map((s) => [s.id, s])));
      } catch (e) {
        setError(String(e));
      }
    })();
  }, []);

  return (
    <div>
      <PageHeader
        title="Review queue"
        description="The two-independent-reviewer rule: a case only joins the golden set once two people, working blind to each other's answer, agree it's correct."
      />
      {error && <ErrorBanner>{error}</ErrorBanner>}

      {cases?.length === 0 ? (
        <EmptyState>Nothing awaiting review.</EmptyState>
      ) : (
        <Table>
          <TableHead columns={["Question", "Suite", "Status"]} />
          <TableBody>
            {cases?.map((c) => (
              <tr key={c.id}>
                <td className="font-medium">
                  <Link className="text-accent hover:text-accent-hover hover:underline" href={`/review/${c.id}`}>
                    {c.question}
                  </Link>
                </td>
                <td className="text-muted">{suites[c.suite_id]?.name ?? c.suite_id}</td>
                <td>
                  <Badge tone={c.status === "needs_resolution" ? "warn" : "neutral"}>{c.status}</Badge>
                </td>
              </tr>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
