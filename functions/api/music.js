import { getStore } from '@netlify/blobs';

export default async function handler() {
  return new Response(JSON.stringify({error:'Cloudflare Worker endpoint required'}), {status:501,headers:{'content-type':'application/json'}});
}
