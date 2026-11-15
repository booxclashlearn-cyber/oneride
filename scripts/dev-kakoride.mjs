import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {readFileSync,existsSync} from 'node:fs';
import path from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url));
const privateEnv=path.join(root,'kakoride/api/.env');
const env={...process.env};
// Only the new server environment is read. The preserved legacy .env.local is unused.
if(existsSync(privateEnv))for(const line of readFileSync(privateEnv,'utf8').split(/\r?\n/)){
  const match=line.match(/^\s*(KAKORIDE_[A-Z_]+)\s*=\s*(.*?)\s*$/);
  if(match&&!Object.hasOwn(env,match[1])&&match[2])env[match[1]]=match[2].replace(/^['"]|['"]$/g,'');
}
const python=env.KAKORIDE_PYTHON||'python';
const children=[
  spawn(python,['-m','uvicorn','kakoride.api.app:app','--host','127.0.0.1','--port','8080','--no-access-log'],{cwd:root,env,stdio:'inherit'}),
  spawn(python,['-m','uvicorn','kakoride.api.app:webhook_app','--host','127.0.0.1','--port','8081','--no-access-log'],{cwd:root,env,stdio:'inherit'}),
  spawn(python,['-m','kakoride.api.worker'],{cwd:root,env,stdio:'inherit'}),
  spawn(process.execPath,[path.join(root,'kakoride/node_modules/vite/bin/vite.js'),'--host','127.0.0.1'],{cwd:path.join(root,'kakoride'),env,stdio:'inherit'}),
];
let stopping=false;
function stop(code=0){if(stopping)return;stopping=true;for(const child of children)child.kill();process.exitCode=code;}
for(const child of children){child.on('error',e=>{console.error(e.message);stop(1);});child.on('exit',code=>stop(code||0));}
process.on('SIGINT',()=>stop());process.on('SIGTERM',()=>stop());
console.log('KaKoRide: web http://127.0.0.1:5173 · API :8080 · webhook-only tunnel port :8081 · persistent reminder worker');
