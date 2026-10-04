export interface MediaEnv { MEDIA: Pick<R2Bucket,'get'|'head'> }
type Context = {request:Request;env:MediaEnv;next:()=>Promise<Response>};

function etagMatches(value:string, etag:string, weak:boolean) {
  return value.trim()==='*' || value.split(',').some(part=>weak ? part.trim().replace(/^W\//,'')===etag : part.trim()===etag);
}

function conditionStatus(headers:Headers, object:R2Object): number | null {
  const match=headers.get('if-match'), none=headers.get('if-none-match');
  const modified=Math.floor(object.uploaded.getTime()/1000)*1000;
  if(match!==null && !etagMatches(match,object.httpEtag,false))return 412;
  const unmodified=headers.get('if-unmodified-since');
  if(match===null && unmodified && modified>Date.parse(unmodified))return 412;
  if(none!==null && etagMatches(none,object.httpEtag,true))return 304;
  const since=headers.get('if-modified-since');
  if(none===null && since && modified<=Date.parse(since))return 304;
  return null;
}

function headersFor(object:R2Object,key:string) {
  const headers=new Headers();
  object.writeHttpMetadata(headers);
  if(!headers.has('content-type'))headers.set('content-type','application/octet-stream');
  headers.set('etag',object.httpEtag);
  headers.set('last-modified',object.uploaded.toUTCString());
  headers.set('accept-ranges','bytes');
  headers.set('x-content-type-options','nosniff');
  headers.set('cache-control',key.startsWith('legacy/')?'public, max-age=31536000, immutable':'public, max-age=3600');
  return headers;
}

function parseRange(value:string|null,size:number): {offset:number;length:number} | 'unsatisfiable' | null {
  if(!value)return null;
  const m=/^bytes=(\d*)-(\d*)$/.exec(value.trim());
  if(!m || (!m[1]&&!m[2]))return null;
  const start=m[1]?Number(m[1]):null, end=m[2]?Number(m[2]):null;
  if((start!==null&&!Number.isSafeInteger(start))||(end!==null&&!Number.isSafeInteger(end)))return null;
  if(start===null){if(!end || !size)return 'unsatisfiable';const length=Math.min(end,size);return {offset:size-length,length};}
  if(end!==null&&end<start)return null;
  if(start>=size)return 'unsatisfiable';
  return {offset:start,length:Math.min(end??size-1,size-1)-start+1};
}

async function serve(request:Request,env:MediaEnv,key:string):Promise<Response> {
  if(request.method!=='GET'&&request.method!=='HEAD')return new Response(null,{status:405,headers:{Allow:'GET, HEAD'}});
  const metadata=await env.MEDIA.head(key);
  if(!metadata)return new Response(null,{status:404});
  const headers=headersFor(metadata,key);
  const precondition=conditionStatus(request.headers,metadata);
  if(precondition)return new Response(null,{status:precondition,headers});
  if(request.method==='HEAD'){headers.set('content-length',String(metadata.size));return new Response(null,{headers});}

  const ifRange=request.headers.get('if-range');
  const rangeAllowed=!ifRange || ifRange===metadata.httpEtag || (!ifRange.includes('"') && Math.floor(metadata.uploaded.getTime()/1000)*1000<=Date.parse(ifRange));
  const range=rangeAllowed?parseRange(request.headers.get('range'),metadata.size):null;
  if(range==='unsatisfiable'){headers.set('content-range',`bytes */${metadata.size}`);return new Response(null,{status:416,headers});}

  const object=await env.MEDIA.get(key,range?{range}:{});
  if(!object)return new Response(null,{status:404});
  const responseHeaders=headersFor(object,key);
  const finalPrecondition=conditionStatus(request.headers,object);
  if(finalPrecondition)return new Response(null,{status:finalPrecondition,headers:responseHeaders});
  if(!('body' in object))return new Response(null,{status:500,headers:responseHeaders});

  const actual=object.range;
  if(range && actual && 'offset' in actual && actual.offset!==undefined && 'length' in actual && actual.length!==undefined){
    responseHeaders.set('content-range',`bytes ${actual.offset}-${actual.offset+actual.length-1}/${object.size}`);
    responseHeaders.set('content-length',String(actual.length));
    return new Response(object.body,{status:206,headers:responseHeaders});
  }
  responseHeaders.set('content-length',String(object.size));
  return new Response(object.body,{headers:responseHeaders});
}

export async function handleMedia(context:Context):Promise<Response> {
  const {request}=context;
  const url=new URL(request.url);
  let pathname:string;
  try { pathname=decodeURIComponent(url.pathname); } catch { return context.next(); }
  if(!pathname.startsWith('/media/'))return context.next();
  return serve(request,context.env,pathname.slice('/media/'.length));
}
