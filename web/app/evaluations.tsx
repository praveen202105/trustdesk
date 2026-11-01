"use client";
import { useState } from "react";
import { Play, CheckCircle2, AlertTriangle, FlaskConical } from "lucide-react";
import { api } from "./api-client";
type Metric = { passed: number; total: number; rate: number | null };
type Report = {
  evaluation_id: string;
  status: string;
  mode?: string;
  total_cases?: number;
  passed_cases?: number;
  errored_cases?: number;
  metrics?: Record<string, Metric>;
  cases?: {
    case_id: string;
    predicted_category?: string;
    predicted_priority?: string;
    passed: boolean;
    citations?: string[];
    error?: string | null;
  }[];
  limitations?: string[];
};
export default function Evaluations() {
  const [report, setReport] = useState<Report | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function run() {
    setBusy(true);
    setError("");
    try {
      const submitted = await api<{ evaluation_id: string }>(
        "/evaluations",
        "POST",
        { suite: "provided" },
      );
      for (let i = 0; i < 180; i++) {
        const current = await api<Report>(
          "/evaluations/" + submitted.evaluation_id,
        );
        setReport(current);
        if (current.status === "succeeded") return;
        if (current.status === "failed")
          throw new Error("Evaluation failed; inspect the recorded job error");
        await new Promise((r) => setTimeout(r, 2000));
      }
      throw new Error(
        "Evaluation is still running. Save its ID and check again shortly.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="evaluations">
      <div className="evaluation-intro">
        <div className="assistant-icon">
          <FlaskConical size={24} />
        </div>
        <div>
          <h2>Evidence you can inspect</h2>
          <p>
            Run the provided cases against the same policy, retrieval and
            guardrail pipeline.
          </p>
        </div>
        <button className="primary" onClick={run} disabled={busy}>
          <Play size={14} />
          {busy ? "Running cases…" : "Run evaluations"}
        </button>
      </div>
      <div className="evaluation-note">
        <AlertTriangle size={15} />
        <span>
          Mock results verify deterministic behavior. They do not establish
          live-model quality. No tool is executed by this runner.
        </span>
      </div>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {report && (
        <>
          <p className="evaluation-status" role="status">
            Evaluation {report.status} · {report.evaluation_id}
          </p>
          {report.metrics && (
            <div className="metrics">
              {Object.entries(report.metrics).map(([name, m]) => (
                <div key={name}>
                  <span>{name.replaceAll("_", " ")}</span>
                  <strong>
                    {m.rate === null ? "N/A" : Math.round(m.rate * 100) + "%"}
                  </strong>
                  <small>
                    {m.passed} / {m.total}
                  </small>
                </div>
              ))}
            </div>
          )}
          {report.cases && (
            <>
              <div className="results-title">
                <CheckCircle2 size={16} />
                <h3>Case results</h3>
                <span>
                  {report.passed_cases} / {report.total_cases} passed ·{" "}
                  {report.errored_cases} errors
                </span>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Case</th>
                      <th>Category</th>
                      <th>Priority</th>
                      <th>Evidence</th>
                      <th>Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.cases.map((c) => (
                      <tr key={c.case_id}>
                        <td>{c.case_id}</td>
                        <td>{c.predicted_category || "—"}</td>
                        <td>{c.predicted_priority || "—"}</td>
                        <td>{c.citations?.join(", ") || c.error || "—"}</td>
                        <td>
                          <span
                            className={
                              "badge " + (c.passed ? "open" : "urgent")
                            }
                          >
                            {c.passed ? "Passed" : "Needs review"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <details className="report-details">
                <summary>Inspect full report and limitations</summary>
                <pre>{JSON.stringify(report, null, 2)}</pre>
              </details>
            </>
          )}
        </>
      )}
    </section>
  );
}
