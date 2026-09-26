import { getStore } from '@netlify/blobs';

const store = getStore('music-hub', { consistency: 'strong' });
const json = (body, status=200) => new Response(JSON.stringify(body), { status, headers: { 'content-type':'application/json; charset=utf-8' } });
const id = () => crypto.randomUUID();

async function readCatalogue(){ return (await store.get('catalogue', { type:'json' })) || { version:1, artists:[], albums:[], tracks:[], playlists:[], videos:[], submissions:[] }; }
async function saveCatalogue(data){ await store.setJSON('catalogue', data); return data; }
function authorized(req){ const token=process.env.MUSIC_ADMIN_TOKEN; return !!token && req.headers.get('authorization') === `Bearer ${token}`; }

export default async (req) => {
  try {
    const url=new URL(req.url);
    const method=req.method.toUpperCase();
    if(method==='GET'){
      const data=await readCatalogue();
      const q=(url.searchParams.get('q')||'').toLowerCase().trim();
      if(!q) return json({ ...data, submissions:undefined });
      const tracks=data.tracks.filter(t=>[t.title,t.artist,t.album,t.genre,t.language].join(' ').toLowerCase().includes(q));
      const artists=data.artists.filter(a=>[a.name,a.bio].join(' ').toLowerCase().includes(q));
      const albums=data.albums.filter(a=>[a.title,a.artist,a.genre].join(' ').toLowerCase().includes(q));
      return json({version:data.version,tracks,artists,albums,playlists:data.playlists,videos:data.videos});
    }
    if(method==='POST'){
      const body=await req.json();
      if(body.action==='submit'){
        const data=await readCatalogue();
        const submission={id:id(),status:'pending',createdAt:new Date().toISOString(),...body.release};
        delete submission.action;
        data.submissions.push(submission);
        await saveCatalogue(data);
        return json({ok:true,id:submission.id,status:submission.status},201);
      }
      if(body.action==='publish'){
        if(!authorized(req)) return json({error:'Unauthorized'},401);
        const data=await readCatalogue();
        const release={id:body.release.id||id(),publishedAt:new Date().toISOString(),...body.release};
        data.tracks=data.tracks.filter(t=>t.id!==release.id); data.tracks.push(release);
        const i=data.submissions.findIndex(s=>s.id===release.id); if(i>=0) data.submissions[i]={...data.submissions[i],status:'published'};
        await saveCatalogue(data); return json({ok:true,release});
      }
      if(body.action==='review'){
        if(!authorized(req)) return json({error:'Unauthorized'},401);
        const data=await readCatalogue(); const i=data.submissions.findIndex(s=>s.id===body.id);
        if(i<0)return json({error:'Submission not found'},404); data.submissions[i].status=body.status||'reviewed'; data.submissions[i].reviewNote=body.note||''; await saveCatalogue(data); return json({ok:true,submission:data.submissions[i]});
      }
      return json({error:'Unknown action'},400);
    }
    if(method==='DELETE'){
      if(!authorized(req)) return json({error:'Unauthorized'},401);
      const data=await readCatalogue(); const type=url.searchParams.get('type'); const itemId=url.searchParams.get('id');
      if(!['tracks','artists','albums','playlists','videos'].includes(type)||!itemId)return json({error:'Invalid deletion request'},400);
      data[type]=data[type].filter(x=>x.id!==itemId); await saveCatalogue(data); return json({ok:true});
    }
    return json({error:'Method not allowed'},405);
  } catch(e){ console.error(e); return json({error:'Music service error'},500); }
};
