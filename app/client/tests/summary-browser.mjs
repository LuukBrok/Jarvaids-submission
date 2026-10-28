/** Fictional transcript, scripted LLM; real HTTP, persistence, canvas and browser. */
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { mkdtempSync, mkdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
const { chromium } = createRequire(import.meta.url)('playwright');
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
const python = process.env.JARVAIDS_TEST_PYTHON || 'python3';
const data = mkdtempSync(join(tmpdir(), 'jv-summary-ui-')), children = [];
const output = resolve(root, '.local/summary-ui'); mkdirSync(output, {recursive:true});
const api = 3097, client = 5197;
function launch(args, cwd) { const child = spawn(python, args, {cwd, stdio:'ignore'}); children.push(child); }
async function ready(url) {
  for (let i=0;i<100;i++) {
    try { const r=await fetch(url); await r.arrayBuffer(); if(r.ok)return; } catch {}
    await new Promise(r=>setTimeout(r,100));
  } throw new Error('Test server did not start');
}
let browser;
try {
  launch(['serve.py','--port',String(client)], resolve(root,'app/client'));
  launch(['-m','tests.summary_browser_server','--port',String(api),'--data-dir',data,'--origin',`http://127.0.0.1:${client}`],resolve(root,'app/server'));
  await ready(`http://127.0.0.1:${api}/health`); await ready(`http://127.0.0.1:${client}/client/`);
  browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||undefined});
  for (const width of [1440,400]) {
    const page=await browser.newPage({viewport:{width,height:1100}}),errors=[],failures=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
    page.on('requestfailed',r=>{if(!/ERR_ABORTED/.test(r.failure()?.errorText||''))failures.push(r.url());});
    page.on('response',r=>{if(r.status()>=400)failures.push(`${r.status()} ${r.url()}`);});
    await page.goto(`http://127.0.0.1:${client}/client/?api=http://127.0.0.1:${api}`);
    await page.locator('#create').click(); await page.locator('#agree-check').check();
    await page.locator('#acknowledge').click(); await page.locator('#activate').click();
    await page.waitForFunction(()=>!document.getElementById('note-text').disabled);
    await page.locator('#note-text').fill('We decided the prototype must work offline.'); await page.locator('#add-note').click();
    await page.locator('#command-menu-button').click();
    await page.locator('#command-menu [data-command="summary"]').click();
    await page.locator('#tab-overview').click();
    await page.getByText('Prototype approach',{exact:true}).first().waitFor();
    await page.locator('#overview-topics > section > details > summary').click();
    await page.locator('#overview-topics').getByText('We decided the prototype must work offline.',{exact:true}).first().waitFor();
    assert.match(await page.locator('#summary-status').innerText(),/1 topic/);
    await page.locator('#zoom-fit').click();
    const note=page.locator('#board .note').filter({hasText:'Prototype approach'});
    await note.getByRole('button',{name:'Show details',exact:true}).click();
    await note.getByText('Design / Prototype approach',{exact:false}).waitFor();
    assert.match(await note.innerText(),/AI summary/);
    assert.equal(await page.evaluate(()=>document.body.scrollWidth<=innerWidth),true,`No body overflow at ${width}`);
    await page.screenshot({path:resolve(output,`overview-${width}.png`),fullPage:true});
    assert.deepEqual(errors,[]);assert.deepEqual(failures,[]);
    await page.close(); console.log(`Summary/canvas/evidence journey at ${width}px: PASS`);
  }
} finally {
  await browser?.close();
  for(const child of children)child.kill();
  await new Promise(r=>setTimeout(r,500));
  if(!resolve(data).startsWith(resolve(tmpdir())+'\\')&&!resolve(data).startsWith(resolve(tmpdir())+'/'))throw new Error('Unsafe scratch path');
  rmSync(data,{recursive:true,force:true});
}
