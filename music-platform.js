/* Music Hub data + local catalogue utilities. Add only authorised/licensed releases. */
const MUSIC_DB={artists:[],albums:[],tracks:[],playlists:[],videos:[],charts:{weekly:[],monthly:[]}};
function musicSearch(q){q=(q||'').toLowerCase().trim();return MUSIC_DB.tracks.filter(t=>[t.title,t.artist,t.album,t.genre,t.language].join(' ').toLowerCase().includes(q));}
function musicGenres(){return [...new Set(MUSIC_DB.tracks.map(t=>t.genre).filter(Boolean))].sort();}
function musicArtist(name){return MUSIC_DB.artists.find(a=>a.name.toLowerCase()===String(name).toLowerCase())||null;}
function musicAlbum(id){return MUSIC_DB.albums.find(a=>a.id===id)||null;}
function musicTrack(id){return MUSIC_DB.tracks.find(t=>t.id===id)||null;}
function musicPlaylist(id){return MUSIC_DB.playlists.find(p=>p.id===id)||null;}
function musicRelated(track){if(!track)return[];return MUSIC_DB.tracks.filter(t=>t.id!==track.id&&(t.artist===track.artist||t.genre===track.genre)).slice(0,8);}
window.MUSIC_DB=MUSIC_DB;
window.MusicHub={search:musicSearch,genres:musicGenres,artist:musicArtist,album:musicAlbum,track:musicTrack,playlist:musicPlaylist,related:musicRelated};
