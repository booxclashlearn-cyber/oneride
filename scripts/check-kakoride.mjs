import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url));
for(const [executable,args,cwd] of [
  [process.env.KAKORIDE_PYTHON||'python',['-m','pytest','kakoride/api/tests','-q'],root],
  [process.execPath,[path.join(root,'kakoride/node_modules/vitest/vitest.mjs'),'run'],path.join(root,'kakoride')],
]){const result=spawnSync(executable,args,{cwd,stdio:'inherit'});if(result.status!==0)process.exit(result.status||1);}
