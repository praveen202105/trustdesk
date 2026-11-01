export type Triage={id:string;category:string;priority:string;escalation_required:boolean;reason:string;sentiment?:string};
export type Ticket={ticket_id:string;customer_id:string;order_id:string|null;subject:string;body:string;created_at:string;status:string;customer_name?:string;triage?:Triage|null};
export type Citation={document_id:string;version_hash:string;chunk_id:string;quote:string;claim:string};
export type Draft={id:string;text:string;citations:Citation[];status:string;escalation_required:boolean;recommended_actions:string[]};
export type Detail={ticket:Ticket;customer:{name:string;tier:string;verified:boolean;country:string}|null;order:{order_id:string;total:number;currency:string;status:string;payment_status:string;items:{name:string;sku:string;quantity:number}[]}|null;triage:Triage|null;draft:Draft|null;warnings:string[]};
