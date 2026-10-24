/** Real Chromium views for the M1 curved tunnel; geometry tests are separate. */
const fs=require('node:fs/promises');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {createHash}=require('node:crypto');
const assert=require('node:assert/strict');
const {launchBrowser}=require('./browser-runtime.cjs');
(async()=>{
 const input=path.resolve(process.argv[2]||'build/duplo-elbow-trial-01');
 const output=path.resolve(process.argv[3]||'build/elbow-browser');
 await fs.mkdir(output,{recursive:true});
 const hash=b=>createHash('sha256').update(b).digest('hex');
 const result={input_files:{},captures:[],errors:[],automated_passed:false,visual_review_performed:false};
 for(const name of ['viewer.html','report.json','brick.stl','brick.step','assembly.step'])result.input_files[name]=hash(await fs.readFile(path.join(input,name)));
 const browser=await launchBrowser();result.browser=browser.version();
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  page.on('pageerror',e=>result.errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')result.errors.push(m.text())});
  await page.goto(pathToFileURL(path.join(input,'viewer.html')).href);
  await page.waitForSelector('#view[data-ready="true"]');
  await page.evaluate(()=>document.fonts.ready);
  async function capture(name){
   await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
   const status=await page.locator('#status').innerText();assert(status.includes('PASS'));
   const pixels=await page.locator('#view').evaluate(canvas=>{
    const gl=canvas.getContext('webgl'),p=new Uint8Array(canvas.width*canvas.height*4);
    gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,p);
    let red=0,blue=0;
    for(let i=0;i<p.length;i+=4){if(p[i]>70&&p[i]>p[i+1]*1.6&&p[i]>p[i+2]*1.5)red++;if(p[i+2]>65&&p[i+2]>p[i]*1.5&&p[i+1]>p[i]*1.5)blue++}
    return {red,blue};
   });
   assert(pixels.red>1500,`${name}: no assembly`);
   if(name.includes('balls')||name.includes('sweep'))assert(pixels.blue>1500,'Ball envelopes missing');
   const png=await page.screenshot({path:path.join(output,name+'.png'),fullPage:true});
   result.captures.push({name,file:name+'.png',sha256:hash(png),pixels,status});
  }
  for(const [name,mode,camera] of [
   ['01-tunnel','single','perspective'],['02-top','single','top'],
   ['03-underside','single','underside'],['04-section','section','section'],
   ['05-cutaway','cutaway','top'],['06-balls','balls','perspective'],
   ['07-sweep','sweep','top'],['08-course','course','perspective'],
   ['09-exploded','exploded','top']]){
   await page.selectOption('#mode',mode);await page.selectOption('#camera',camera);
   await capture(name);
  }
  await page.selectOption('#mode','single');
  await page.setViewportSize({width:390,height:844});await capture('10-mobile');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile overflow');
  assert(new Set(result.captures.map(x=>x.sha256)).size===result.captures.length);
  assert.deepEqual(result.errors,[]);result.automated_passed=true;
 }catch(e){result.errors.push(String(e));throw e}
 finally{
  await browser.close();
  await fs.writeFile(path.join(output,'browser-report.json'),JSON.stringify(result,null,2)+'\n');
 }
 console.log('ELBOW browser PASS: '+result.captures.length+' views');
})().catch(e=>{console.error(e);process.exitCode=1});
