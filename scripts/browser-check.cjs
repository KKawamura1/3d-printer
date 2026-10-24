/** Real Chromium QA and screenshots; no mocked DOM or canvas. */
const {chromium}=require('playwright');
const fs=require('node:fs/promises');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {createHash}=require('node:crypto');
const assert=require('node:assert/strict');

(async()=>{
 const input=path.resolve(process.argv[2]||'build/duplo-2x4');
 const output=path.resolve(process.argv[3]||'build/browser-qa');
 await fs.mkdir(output,{recursive:true});
 const cadReport=JSON.parse(await fs.readFile(path.join(input,'report.json'),'utf8'));
 const expectedCollision=!!cadReport.intentional_fit_trial;
 const hash=b=>createHash('sha256').update(b).digest('hex');
 const result={schema_version:1,browser:null,input_files:{},captures:[],errors:[],automated_passed:false,visual_review_performed:false};
 for(const name of ['viewer.html','report.json','brick.stl'])result.input_files[name]=hash(await fs.readFile(path.join(input,name)));
 let browser,context,page;
 try{
  const {launchBrowser}=require('./browser-runtime.cjs');
  browser=await launchBrowser();
  result.browser=browser.version();
  context=await browser.newContext({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  await context.tracing.start({screenshots:true,snapshots:true,sources:true});
  page=await context.newPage();
  page.on('pageerror',e=>result.errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')result.errors.push(m.text())});
  page.on('requestfailed',r=>result.errors.push(`${r.url()}: ${r.failure()?.errorText}`));
  await page.goto(pathToFileURL(path.join(input,'viewer.html')).href);
  await page.waitForSelector('#view[data-ready="true"]');
  await page.evaluate(()=>document.fonts.ready);
  async function set(id,value){await page.selectOption('#'+id,value)}
  async function slide(value){await page.locator('#lift').fill(String(value));await page.locator('#lift').dispatchEvent('input')}
  async function capture(name,blue=false){
   await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
   const pixels=await page.locator('#view').evaluate(canvas=>{
    const gl=canvas.getContext('webgl');const d=new Uint8Array(canvas.width*canvas.height*4);gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,d);
    let red=0,blue=0;
    for(let i=0;i<d.length;i+=4){if(d[i]>70&&d[i]>d[i+1]*1.6&&d[i]>d[i+2]*1.5)red++;if(d[i+2]>65&&d[i+2]>d[i]*1.5&&d[i+1]>d[i]*1.5)blue++}
    return {red,blue};
   });
   assert(pixels.red>4000,`${name}: red model missing or blank canvas`);
   if(blue)assert(pixels.blue>4000,`${name}: upper blue brick missing`);
   const status=await page.locator('#status').innerText();
   const png=await page.screenshot({path:path.join(output,name+'.png'),fullPage:true});
   result.captures.push({name,file:name+'.png',sha256:hash(png),pixels,status});
   console.log(`${name}: ${status}`);
  }
  await capture('01-perspective');
  await set('camera','top');await capture('02-top');
  await set('camera','underside');await capture('03-underside');
  await set('mode','section');await set('camera','section');await capture('04-section');
  await set('mode','stack');await set('camera','perspective');await capture('05-assembled',true);
  assert((await page.locator('#status').innerText()).endsWith(expectedCollision?'あり':'検出なし'));
  await slide(8);await capture('06-exploded',true);
  assert((await page.locator('#status').innerText()).includes('未計算'));
  await slide(0);await set('pose','cross_90');await capture('07-cross-90',true);
  assert((await page.locator('#status').innerText()).endsWith(expectedCollision?'あり':'検出なし'));
  await set('pose','half_pitch_negative_control');await capture('08-collision-control',true);
  assert((await page.locator('#status').innerText()).endsWith('あり'));
  await set('mode','single');await set('camera','perspective');
  const before=await page.locator('#view').getAttribute('data-frame');
  const bounds=await page.locator('#view').boundingBox();
  await page.mouse.move(bounds.x+bounds.width/2,bounds.y+bounds.height/2);
  await page.mouse.down();await page.mouse.move(bounds.x+bounds.width/2+120,bounds.y+bounds.height/2+60,{steps:5});await page.mouse.up();
  await page.mouse.wheel(0,-200);
  assert(+(await page.locator('#view').getAttribute('data-frame'))>+before,'pointer/wheel did not redraw');
  await capture('09-orbit-zoom');
  await page.setViewportSize({width:390,height:844});await page.locator('#under').click();await capture('10-mobile');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'horizontal overflow on mobile');
  assert.equal(new Set(result.captures.map(c=>c.sha256)).size,result.captures.length,'Views did not change');
  assert.deepEqual(result.errors,[],'Browser errors');
  result.automated_passed=true;
 }catch(e){
  result.errors.push(e.stack||String(e));
  if(page)await page.screenshot({path:path.join(output,'failure.png'),fullPage:true}).catch(()=>{});
  process.exitCode=1;
 }finally{
  if(context)await context.tracing.stop({path:path.join(output,'trace.zip')}).catch(()=>{});
  if(browser)await browser.close();
  await fs.writeFile(path.join(output,'browser-report.json'),JSON.stringify(result,null,2)+'\n');
 }
 if(!result.automated_passed)throw Error(result.errors.join('\n'));
})().catch(e=>{console.error(e);process.exitCode=1});

