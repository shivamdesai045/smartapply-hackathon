import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const value=process.env.RENDER_BACKEND_URL;
if(!value) throw new Error('Set RENDER_BACKEND_URL to your Render service HTTPS origin.');
const backend=new URL(value);
if(backend.protocol!=='https:'||backend.username||backend.password||backend.pathname!=='/'||backend.search||backend.hash)
 throw new Error('RENDER_BACKEND_URL must be an HTTPS origin without credentials or path.');
if(process.env.VITE_API_BASE) throw new Error('Leave VITE_API_BASE empty; production uses the same-origin API proxy.');
const output=path.join(root,'.vercel/output');
fs.mkdirSync(output,{recursive:true});
fs.cpSync(path.join(root,'dist'),path.join(output,'static'),{recursive:true});
fs.writeFileSync(path.join(output,'config.json'),JSON.stringify({version:3,routes:[
 {src:'/api/(.*)',dest:backend.origin+'/api/$1',headers:{'Cache-Control':'no-store'}},
 {handle:'filesystem'},
 {src:'/(.*)',dest:'/index.html'}
]},null,2));
console.log('Vercel output generated with same-origin API proxy and SPA routes.');
