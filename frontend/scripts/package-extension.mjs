// Package only extension runtime files. No project source, credentials or user data.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const frontend=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const source=path.resolve(frontend,'../sahayak-autofill/autofill-ext');
const names=['manifest.json','background.js','content.js','app.html','app.js','app.css'];
for(const dir of ['lib','icons']) for(const name of fs.readdirSync(path.join(source,dir)).sort()) {
 if(/\.(js|png|svg|ico)$/.test(name)&&fs.statSync(path.join(source,dir,name)).isFile()) names.push(`${dir}/${name}`);
}
const origins=['http://127.0.0.1:5173','http://localhost:5173'];
const deployed=process.env.SAHAYAK_APP_ORIGIN || (process.env.VERCEL_PROJECT_PRODUCTION_URL ? 'https://'+process.env.VERCEL_PROJECT_PRODUCTION_URL : '');
if(process.env.VERCEL==='1'&&!deployed) throw new Error('Set SAHAYAK_APP_ORIGIN to the stable production website HTTPS origin.');
if(deployed){
 const url=new URL(deployed);
 if(url.protocol!=='https:'||url.username||url.password||url.pathname!=='/'||url.search||url.hash) throw new Error('SAHAYAK_APP_ORIGIN must be an exact HTTPS origin.');
 origins.push(url.origin);
}
const entries=names.map(name=>{
 let data=fs.readFileSync(path.join(source,name));
 if(['background.js','content.js'].includes(name)){
  const literal="['http://127.0.0.1:5173','http://localhost:5173']";
  if(!data.toString().includes(literal))throw new Error('Extension origin allowlist source changed; update packager.');
  data=Buffer.from(data.toString().replace(literal,JSON.stringify(origins)));
 }
 return {name,data};
});
entries.push({name:'INSTALL.txt',data:Buffer.from('Sahayak AutoFill\n\n1. Extract this ZIP to a folder you will keep.\n2. Open chrome://extensions in Chrome.\n3. Turn on Developer mode.\n4. Click Load unpacked and select the extracted folder containing manifest.json.\n5. Refresh the application website in the same Chrome profile.\n6. Review your details, open the official portal from the app, and click Fill reviewed details.\n\nDo not delete the extracted folder while using the extension. Installing from a ZIP is manual; downloading does not install the extension.\n')});
function crc32(data){let crc=0xffffffff;for(const byte of data){crc^=byte;for(let i=0;i<8;i++)crc=(crc>>>1)^((crc&1)?0xedb88320:0);}return (crc^0xffffffff)>>>0;}
const local=[],central=[];let offset=0;
for(const {name,data} of entries){
 const filename=Buffer.from(name);const crc=crc32(data);
 const header=Buffer.alloc(30);header.writeUInt32LE(0x04034b50);header.writeUInt16LE(20,4);header.writeUInt16LE(0x5021,12);header.writeUInt32LE(crc,14);header.writeUInt32LE(data.length,18);header.writeUInt32LE(data.length,22);header.writeUInt16LE(filename.length,26);
 local.push(header,filename,data);
 const directory=Buffer.alloc(46);directory.writeUInt32LE(0x02014b50);directory.writeUInt16LE(20,4);directory.writeUInt16LE(20,6);directory.writeUInt16LE(0x5021,14);directory.writeUInt32LE(crc,16);directory.writeUInt32LE(data.length,20);directory.writeUInt32LE(data.length,24);directory.writeUInt16LE(filename.length,28);directory.writeUInt32LE(offset,42);
 central.push(directory,filename);offset+=header.length+filename.length+data.length;
}
const directory=Buffer.concat(central);const end=Buffer.alloc(22);end.writeUInt32LE(0x06054b50);end.writeUInt16LE(entries.length,8);end.writeUInt16LE(entries.length,10);end.writeUInt32LE(directory.length,12);end.writeUInt32LE(offset,16);
const destination=path.join(frontend,'public/downloads/sahayak-autofill.zip');fs.mkdirSync(path.dirname(destination),{recursive:true});fs.writeFileSync(destination,Buffer.concat([...local,directory,end]));
console.log(`Extension ZIP generated: ${entries.length} runtime/install files.`);
