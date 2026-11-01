"use client";
import {useEffect,useState} from "react";
import {Check,ShieldCheck,X} from "lucide-react";
import {api} from "./api-client";
import type {Detail} from "./types";
type Proposal={proposal_id:string;state:string;arguments:{order_id:string;reason:string;amount:string};execution_job_id:string|null;result:{external_review_id:string;money_refunded:boolean}|null};
export default function Approval({detail}:{detail:Detail}){
 const [proposal,setProposal]=useState<Proposal|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
 useEffect(()=>{let active=true;api<{items:Proposal[]}>(`/tickets/${detail.ticket.ticket_id}/action-proposals`).then(d=>{if(active)setProposal(d.items[0]||null);}).catch(()=>{});return()=>{active=false;};},[detail.ticket.ticket_id,detail.draft?.id]);
 async function prepare(){if(!detail.draft)return;setBusy(true);setError("");try{setProposal(await api(`/tickets/${detail.ticket.ticket_id}/action-proposals`,"POST",{draft_id:detail.draft.id}));}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 async function decide(decision:"approved"|"rejected"){
  if(!proposal)return;setBusy(true);setError("");try{
   const updated=await api<Proposal>(`/action-proposals/${proposal.proposal_id}/decision`,"POST",{decision,reason:"Reviewed the policy evidence and proposed arguments"});setProposal(updated);
   if(updated.execution_job_id){
    for(let i=0;i<60;i++){await new Promise(r=>setTimeout(r,2000));const job=await api<{status:string;error?:{message:string}}>("/jobs/"+updated.execution_job_id);if(job.status==="failed")throw new Error(job.error?.message||"Execution failed safely");if(job.status==="succeeded"){setProposal(await api("/action-proposals/"+proposal.proposal_id));return;}}
    throw new Error("Review execution is still pending. Refresh to check its state.");
   }
  }catch(e){setError((e as Error).message);}finally{setBusy(false);}
 }
 const available=detail.draft?.status==="ready_for_review"&&detail.draft.recommended_actions.includes("start_refund_review");
 if(!available&&!proposal)return null;
 return <div className="approval-panel"><div className="approval-title"><ShieldCheck size={16}/><strong>Human approval</strong><span className="badge">{proposal?.state||"Not requested"}</span></div>{proposal?<><p>Start a refund review for <strong>{proposal.arguments.order_id}</strong></p><dl><dt>Review amount</dt><dd>{detail.order?.currency} {proposal.arguments.amount}</dd><dt>Reason</dt><dd>{proposal.arguments.reason}</dd></dl>{proposal.state==="proposed"&&<div className="approval-buttons"><button className="primary" disabled={busy} onClick={()=>decide("approved")}><Check size={14}/> Approve review</button><button className="secondary" disabled={busy} onClick={()=>decide("rejected")}><X size={14}/> Reject</button></div>}{proposal.state==="succeeded"&&<div className="review-success"><Check size={14}/> Review requested <small>{proposal.result?.external_review_id}</small></div>}{proposal.state==="rejected"&&<p>The proposal was rejected. No action was executed.</p>}{busy&&<p role="status">Processing review…</p>}</>:<><p>Prepare an approval request using the policy-backed draft.</p><button className="secondary" onClick={prepare} disabled={busy}>Prepare refund review</button></>}<small className="approval-footnote">A review request does not issue a refund. No money has been refunded.</small>{error&&<div className="error" role="alert">{error}</div>}</div>;
}
