// Optional integration helper: uses an existing Playwright/Chromium installation.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {spawn}=require('node:child_process');
const path=require('node:path');
const fs=require('node:fs/promises');
(async()=>{
 const folder=path.resolve(process.argv[2]);
 const server=spawn(process.env.PYTHON_EXE||'python',['-m','http.server','9791','--bind','127.0.0.1','--directory',folder],{stdio:'ignore',windowsHide:true});
 let browser;
 try{
  browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_EXE||undefined,proxy:process.env.BROWSER_PROXY?{server:process.env.BROWSER_PROXY,bypass:'127.0.0.1,localhost'}:undefined});
  const page=await browser.newPage({viewport:{width:960,height:540}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  for(let i=0;i<30;i++){try{await page.goto('http://127.0.0.1:9791/');break;}catch(e){if(i===29)throw e;await new Promise(r=>setTimeout(r,200));}}
  await page.waitForFunction(()=>window.sceneReady===true,{},{timeout:60000});
  await page.locator('aside').evaluate(el=>el.style.visibility='hidden');
  await page.evaluate(()=>window.renderAt(2));const first=await page.locator('canvas').screenshot();
  await page.evaluate(()=>window.renderAt(7));await page.evaluate(()=>window.renderAt(2));
  if(!first.equals(await page.locator('canvas').screenshot()))throw Error('Non-deterministic frame evaluation');
  await page.screenshot({path:path.join(folder,'browser.png')});
  await fs.writeFile(path.join(folder,'probes.json'),JSON.stringify(await page.evaluate(()=>window.testProbes)));
  await page.locator('aside').evaluate(el=>el.style.visibility='visible');
  for(const [button,file] of [['下载 GLB','asset.glb'],['下载交接清单','asset.transfer.json']]){
   const next=page.waitForEvent('download');await page.getByRole('button',{name:button,exact:true}).click();await(await next).saveAs(path.join(folder,file));
  }
  // Verify exporting did not alter the visible source scene.
  await page.locator('aside').evaluate(el=>el.style.visibility='hidden');
  await page.evaluate(()=>window.renderAt(2));
  if(!first.equals(await page.locator('canvas').screenshot()))throw Error('Export changed source scene');
  if(errors.length)throw Error(errors.join('\n'));
  console.log(JSON.stringify({status:'passed',browser:await browser.version(),deterministic:true,source_preserved:true}));
 }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
