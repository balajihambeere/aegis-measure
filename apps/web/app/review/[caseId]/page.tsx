"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  AnswerBlock,
  Badge,
  Button,
  Card,
  ErrorBanner,
  Label,
  Muted,
  PageHeader,
  Select,
  Table,
  TableBody,
  TextArea,
  TextInput,
} from "@/components/ui";
import { api, GoldenCase, ReviewStatus } from "@/lib/api";

export default function CaseReviewPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const router = useRouter();
  const [goldenCase, setGoldenCase] = useState<GoldenCase | null>(null);
  const [status, setStatus] = useState<ReviewStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [reviewerName, setReviewerName] = useState("");
  const [proposedAnswer, setProposedAnswer] = useState("");

  const [decision, setDecision] = useState<"approve" | "needs_resolution">("approve");
  const [resolvedBy, setResolvedBy] = useState("");
  const [referenceAnswer, setReferenceAnswer] = useState("");
  const [notes, setNotes] = useState("");

  async function load() {
    if (!caseId) return;
    try {
      const [c, s] = await Promise.all([api.getCase(caseId), api.getReviewStatus(caseId)]);
      setGoldenCase(c);
      setStatus(s);
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId]);

  async function submitReview(e: React.FormEvent) {
    e.preventDefault();
    if (!caseId || !reviewerName.trim() || !proposedAnswer.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.submitReview(caseId, reviewerName.trim(), proposedAnswer.trim());
      // Clear both fields, not just the answer — this form may be reused by
      // a second, different reviewer in the same browser session, and the
      // first reviewer's name should not linger as a trap to type into.
      setReviewerName("");
      setProposedAnswer("");
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function resolve(e: React.FormEvent) {
    e.preventDefault();
    if (!caseId || !resolvedBy.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.resolveCase(caseId, {
        decision,
        resolved_by: resolvedBy.trim(),
        reference_answer: decision === "approve" ? referenceAnswer.trim() : undefined,
        notes: notes.trim(),
      });
      router.push("/review");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!goldenCase || !status) return <Muted>Loading…</Muted>;

  const needsMoreReviews = status.submission_count < 2;
  const alreadyDecided = goldenCase.status === "approved" || goldenCase.status === "retired";

  return (
    <div>
      <PageHeader back={{ href: "/review", label: "Review queue" }} title={goldenCase.question} />
      {goldenCase.context && (
        <>
          <Label>Context</Label>
          <AnswerBlock>{goldenCase.context}</AnswerBlock>
        </>
      )}
      {error && <ErrorBanner>{error}</ErrorBanner>}

      {alreadyDecided ? (
        <Card className={goldenCase.context ? "mt-4" : undefined}>
          <p className="mb-2">
            <Badge tone={goldenCase.status === "approved" ? "pass" : "neutral"}>
              {goldenCase.status}
            </Badge>
          </p>
          {goldenCase.reference_answer && (
            <>
              <Label>Reference answer</Label>
              <AnswerBlock>{goldenCase.reference_answer}</AnswerBlock>
            </>
          )}
          <Muted className="mt-2">
            Resolved by {goldenCase.resolved_by} — {goldenCase.resolution_notes || "no notes"}
          </Muted>
        </Card>
      ) : (
        <>
          <Card className={goldenCase.context ? "mt-4" : undefined}>
            <h3 className="text-sm font-semibold text-ink">
              Independent reviews ({status.submission_count}/2)
            </h3>
            {needsMoreReviews ? (
              <Muted className="mt-2">
                {status.reviewer_names.length > 0
                  ? `Submitted so far: ${status.reviewer_names.join(", ")}. Their answers stay ` +
                    "hidden until a second, independent review comes in — that's the whole point " +
                    "of the rule."
                  : "No reviews yet."}
              </Muted>
            ) : (
              <Table>
                <TableBody>
                  {status.submissions?.map((s) => (
                    <tr key={s.id}>
                      <td className="w-1/4 font-medium">{s.reviewer_name}</td>
                      <td>{s.proposed_answer}</td>
                    </tr>
                  ))}
                </TableBody>
              </Table>
            )}
          </Card>

          {needsMoreReviews && (
            <Card className="max-w-lg">
              <h4 className="text-sm font-semibold text-ink">Submit an independent review</h4>
              <form onSubmit={submitReview}>
                <Label htmlFor="reviewer-name">Your name</Label>
                <TextInput
                  id="reviewer-name"
                  value={reviewerName}
                  onChange={(e) => setReviewerName(e.target.value)}
                />
                <Label htmlFor="proposed-answer">What&apos;s the correct answer?</Label>
                <TextArea
                  id="proposed-answer"
                  rows={3}
                  value={proposedAnswer}
                  onChange={(e) => setProposedAnswer(e.target.value)}
                />
                <Button type="submit" disabled={busy} className="mt-4">
                  Submit review
                </Button>
              </form>
            </Card>
          )}

          {!needsMoreReviews && (
            <Card className="max-w-lg">
              <h4 className="text-sm font-semibold text-ink">Resolve</h4>
              <Muted className="mt-1 text-xs">
                If the two answers above genuinely agree, approve with a reference answer. If they
                disagree because the underlying source material is ambiguous, flag it instead —
                that&apos;s not a grading problem to paper over.
              </Muted>
              <form onSubmit={resolve}>
                <Label htmlFor="decision">Decision</Label>
                <Select
                  id="decision"
                  value={decision}
                  onChange={(e) => setDecision(e.target.value as "approve" | "needs_resolution")}
                >
                  <option value="approve">Approve</option>
                  <option value="needs_resolution">Flag as needs resolution (ambiguous source)</option>
                </Select>
                <Label htmlFor="resolved-by">Your name</Label>
                <TextInput id="resolved-by" value={resolvedBy} onChange={(e) => setResolvedBy(e.target.value)} />
                {decision === "approve" && (
                  <>
                    <Label htmlFor="reference-answer">Reference answer</Label>
                    <TextArea
                      id="reference-answer"
                      rows={3}
                      value={referenceAnswer}
                      onChange={(e) => setReferenceAnswer(e.target.value)}
                    />
                  </>
                )}
                <Label htmlFor="notes">Notes</Label>
                <TextArea id="notes" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
                <Button type="submit" disabled={busy} className="mt-4">
                  Submit decision
                </Button>
              </form>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
