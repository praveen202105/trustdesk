"use client";
import { useState } from "react";
import {
  ShieldCheck,
  Sparkles,
  FileText,
  Activity,
  LoaderCircle,
  ExternalLink,
} from "lucide-react";
import Approval from "./approval";
import { api } from "./api-client";
import type { Detail } from "./types";

export default function Assistant({
  detail,
  onRefresh,
}: {
  detail: Detail;
  onRefresh: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [source, setSource] = useState<{ title: string; content: string } | null>(
      null,
    ),
    [trace, setTrace] = useState<unknown>(null);
  async function run(kind: string) {
    setBusy(kind);
    setError("");
    try {
      const submitted = await api<{ job_id: string }>(
        `/tickets/${detail.ticket.ticket_id}/${kind}`,
        "POST",
        {},
      );
      for (let count = 0; count < 120; count++) {
        await new Promise((r) => setTimeout(r, count < 15 ? 2000 : 10000));
        const job = await api<{ status: string; error?: { message: string } }>(
          "/jobs/" + submitted.job_id,
        );
        if (job.status === "failed")
          throw new Error(job.error?.message || "Operation failed safely");
        if (job.status === "succeeded") {
          await onRefresh();
          return;
        }
      }
      throw new Error(
        "The job is still running. Refresh the ticket to check progress.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  return (
    <section className="assistant">
      <div className="assistant-title">
        <span>
          <Sparkles size={17} /> AI assistant
        </span>
        <span className="badge open">Evidence-led</span>
      </div>
      <div className="assistant-actions">
        <button
          className="secondary"
          disabled={!!busy}
          onClick={() => run("triage")}
        >
          {busy === "triage" ? (
            <LoaderCircle size={14} className="spin" />
          ) : (
            <ShieldCheck size={14} />
          )}{" "}
          Triage ticket
        </button>
        <button
          className="primary"
          disabled={!!busy || !detail.triage}
          onClick={() => run("drafts")}
        >
          {busy === "drafts" ? (
            <LoaderCircle size={14} className="spin" />
          ) : (
            <FileText size={14} />
          )}{" "}
          Generate draft
        </button>
      </div>
      {busy && (
        <p className="job-note" role="status">
          Processing {busy} in the background…
        </p>
      )}
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {detail.triage && (
        <div className="triage">
          <div>
            <span className="badge">
              {detail.triage.category.replace("_", " ")}
            </span>
            <span className={"badge " + detail.triage.priority}>
              {detail.triage.priority}
            </span>
            {detail.triage.escalation_required && (
              <span className="badge urgent">Human review</span>
            )}
          </div>
          <p>{detail.triage.reason}</p>
        </div>
      )}
      {detail.draft && (
        <div className="draft">
          <div className="draft-heading">
            <FileText size={15} /> Draft reply{" "}
            <span>{detail.draft.status.replaceAll("_", " ")}</span>
          </div>
          <p>{detail.draft.text}</p>
          <div className="citation-list">
            {detail.draft.citations.map((c) => (
              <button
                key={c.chunk_id}
                className="citation"
                onClick={async () => {
                  try {
                    setSource(
                      await api(
                        `/knowledge/documents/${c.document_id}?version_hash=${c.version_hash}`,
                      ),
                    );
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                <ExternalLink size={11} />
                {c.document_id}
              </button>
            ))}
          </div>
          <p className="draft-note">
            Internal draft · review before responding to the customer
          </p>
          {!!detail.draft.recommended_actions.length && (
            <div className="recommendations">
              <strong>Recommended next steps</strong>
              {detail.draft.recommended_actions.map((action) => (
                <span key={action}>
                  {action.replaceAll("_", " ")}
                  {action !== "escalate_to_human" &&
                    " · approval required before sensitive execution"}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
      <Approval detail={detail} />
      <button
        className="trace-link"
        onClick={async () => {
          try {
            setTrace(await api(`/tickets/${detail.ticket.ticket_id}/traces`));
          } catch (e) {
            setError((e as Error).message);
          }
        }}
      >
        <Activity size={12} /> Inspect decision traces
      </button>
      {source && (
        <div className="modal-backdrop">
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label="Policy source"
          >
            <button className="close-modal" onClick={() => setSource(null)}>
              Close
            </button>
            <h3>{source.title}</h3>
            <pre>{source.content}</pre>
          </div>
        </div>
      )}
      {trace !== null && (
        <div className="modal-backdrop">
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label="Decision traces"
          >
            <button className="close-modal" onClick={() => setTrace(null)}>
              Close
            </button>
            <h3>Decision traces</h3>
            <pre>{JSON.stringify(trace, null, 2)}</pre>
          </div>
        </div>
      )}
    </section>
  );
}
