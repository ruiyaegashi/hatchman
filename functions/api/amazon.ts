import mapping from '../../affiliate/mapping.json';
interface Env { AMAZON_CREATORS_CREDENTIAL_ID:string; AMAZON_CREATORS_CREDENTIAL_SECRET:string; AMAZON_CREATORS_VERSION:string; AMAZON_ASSOCIATE_TAG:string }
const allowedAsins=new Set(mapping.articles.flatMap((article)=>article.products.filter((product)=>product.display_status==='approved').map((product)=>product.current_asin)));
let tokenCache:{value:string;expires:number}|undefined;
function tokenEndpoint(version:string){return version.startsWith('3.3')?'https://api.amazon.co.jp/auth/o2/token':version.startsWith('3.2')?'https://api.amazon.co.uk/auth/o2/token':'https://api.amazon.com/auth/o2/token'}
async function accessToken(env:Env){
  if(tokenCache && tokenCache.expires>Date.now()+60_000)return tokenCache.value;
  const response=await fetch(tokenEndpoint(env.AMAZON_CREATORS_VERSION),{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({grant_type:'client_credentials',client_id:env.AMAZON_CREATORS_CREDENTIAL_ID,client_secret:env.AMAZON_CREATORS_CREDENTIAL_SECRET,scope:'creatorsapi::default'})});
  if(!response.ok)throw new Error(`Creators API token error ${response.status}`);
  const data=await response.json() as {access_token:string;expires_in:number}; tokenCache={value:data.access_token,expires:Date.now()+data.expires_in*1000}; return data.access_token;
}
export const onRequestGet=async(context:{request:Request;env:Env})=>{
  try{
    const url=new URL(context.request.url); const asins=(url.searchParams.get('asins')??'').split(',').filter(Boolean);
    if(asins.length<1||asins.length>10||asins.some((x)=>!/^[A-Z0-9]{10}$/.test(x)||!allowedAsins.has(x)))return Response.json({error:'invalid ASIN list'},{status:400});
    const token=await accessToken(context.env); const response=await fetch('https://creatorsapi.amazon/catalog/v1/getItems',{method:'POST',headers:{authorization:`Bearer ${token}`,'content-type':'application/json','x-marketplace':'www.amazon.co.jp'},body:JSON.stringify({itemIds:asins,itemIdType:'ASIN',marketplace:'www.amazon.co.jp',partnerTag:context.env.AMAZON_ASSOCIATE_TAG,resources:['images.primary.medium','itemInfo.title']})});
    if(!response.ok)return Response.json({error:'Creators API request failed'},{status:502});
    const data=await response.json() as any; const source=data.itemsResult?.items??[];
    const items=source.map((item:any)=>({asin:item.asin,title:item.itemInfo?.title?.displayValue??item.asin,url:item.detailPageURL,image:item.images?.primary?.medium?.url}));
    return Response.json({items,disclaimer:'Amazonの商品情報は変更または削除される場合があります。'},{headers:{'cache-control':'public, max-age=3600, s-maxage=21600'}});
  }catch{return Response.json({error:'Amazon product data is unavailable'},{status:503});}
};
