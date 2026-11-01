import { NextRequest } from "next/server";
export const dynamic = "force-dynamic";
async function proxy(request:NextRequest, context:{params:Promise<{path:string[]}>}){
  const {path}=await context.params;
  const base=process.env.API_INTERNAL_URL || "http://localhost:8000";
  const target=new URL("/api/v1/"+path.map(encodeURIComponent).join("/"),base);
  target.search=request.nextUrl.search;
  const headers=new Headers();
  for(const key of ["content-type","cookie","origin","idempotency-key"]) {const value=request.headers.get(key);if(value)headers.set(key,value);}
  try{
    const upstream=await fetch(target,{method:request.method,headers,body:["GET","HEAD"].includes(request.method)?undefined:await request.text(),cache:"no-store",signal:AbortSignal.timeout(15000)});
    const outgoing=new Headers();
    for(const key of ["content-type","set-cookie","x-request-id","retry-after"]) {const value=upstream.headers.get(key);if(value)outgoing.set(key,value);}
    outgoing.set("cache-control","no-store");
    return new Response(upstream.status===204?null:await upstream.text(),{status:upstream.status,headers:outgoing});
  }catch{return Response.json({error:{code:"API_UNAVAILABLE",message:"Support API is unavailable. Please try again."}},{status:503});}
}
export const GET=proxy; export const POST=proxy; export const DELETE=proxy;
