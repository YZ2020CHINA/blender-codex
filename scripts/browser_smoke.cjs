// Optional local browser integration check. PLAYWRIGHT_MODULE can name an installed Playwright directory.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {spawn}=require('node:child_process');const fs=require('node:fs/promises');const path=require('node:path');
(async()=>{
 const root=path.resolve(__dirname,'..');
 const server=spawn('python',['-X','utf8','-m','http.server','9784','--bind','127.0.0.1','--directory',path.join(root,'.state')],{stdio:'ignore',windowsHide:true});
 let browser;
 try{
  browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_EXE||undefined,proxy:process.env.BROWSER_PROXY?{server:process.env.BROWSER_PROXY,bypass:'127.0.0.1,localhost'}:undefined});
  const page=await browser.newPage({viewport:{width:960,height:540}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  for(let n=0;n<30;n++){try{await page.goto('http://127.0.0.1:9784/');break;}catch(e){if(n===29)throw e;await new Promise(r=>setTimeout(r,200));}}
  await page.goto('http://127.0.0.1:9784/authoring-qa/');await page.waitForFunction(()=>window.sceneReady===true,{},{timeout:60000});
  await page.evaluate(()=>window.renderAt(2));await page.screenshot({path:path.join(root,'.state/authoring-qa/screenshot.png')});
  const first=await page.locator('canvas').screenshot();await page.evaluate(()=>window.renderAt(7));await page.evaluate(()=>window.renderAt(2));const second=await page.locator('canvas').screenshot();
  if(!first.equals(second))throw Error('evaluate(t) is not deterministic');
  const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'下载 GLB'}).click();const download=await downloadPromise;await download.saveAs(path.join(root,'.state/authoring-qa/export.glb'));
  const states=(await fs.readdir(path.join(root,'.state'))).filter(n=>n.startsWith('integration-')).sort();const latest=states.at(-1);
  await page.goto(`http://127.0.0.1:9784/${latest}/web/`);await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('已载入'),{},{timeout:60000});
  await page.screenshot({path:path.join(root,'.state/viewer-screenshot.png')});
  if(errors.length)throw Error(errors.join('\n'));console.log(JSON.stringify({status:'passed',deterministic:true,glb:'export.glb',viewer:await page.locator('#status').textContent(),browser:await browser.version()}));
 }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
