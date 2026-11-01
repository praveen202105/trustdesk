export async function api<T>(path:string,method="GET",body?:unknown):Promise<T>{
 const response=await fetch("/api/v1"+path,{method,headers:{"Content-Type":"application/json",...(method!=="GET"?{"Idempotency-Key":crypto.randomUUID()}: {})},body:body===undefined?undefined:JSON.stringify(body)});
 if(!response.ok){const data=await response.json();throw new Error(data.error?.message || "Request failed");}
 return response.status===204?undefined as T:response.json();
}
