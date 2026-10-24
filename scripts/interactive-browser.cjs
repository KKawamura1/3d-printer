/** Keep a real browser/tab alive. JSON-lines commands arrive over stdin. */
const fs=require('node:fs/promises');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const readline=require('node:readline');
const {launchBrowser}=require('./browser-runtime.cjs');
(async()=>{
 const input=path.resolve(process.argv[2]||'build/duplo-2x4');
 const out=path.resolve(process.argv[3]||'build/interactive');await fs.mkdir(out,{recursive:true});
 const browser=await launchBrowser();
 const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(path.join(input,'viewer.html')).href);
 await page.waitForSelector('#view[data-ready="true"]');
 await page.evaluate(()=>document.fonts.ready);
 let number=0;
 console.log(JSON.stringify({ready:true,browser:browser.version(),commands:['view','mode','pose','lift','orbit','zoom','reload','capture','close']}));
 const lines=readline.createInterface({input:process.stdin,terminal:false});
 for await(const line of lines){
  if(!line.trim())continue;
  const start=performance.now();let request;
  try{
   request=JSON.parse(line);
   const {action,value}=request;
   if(action==='close')break;
   if(['view','mode','pose'].includes(action))await page.selectOption(action==='view'?'#camera':'#'+action,value);
   else if(action==='lift'){await page.locator('#lift').fill(String(value));await page.locator('#lift').dispatchEvent('input')}
   else if(action==='orbit'){
    const b=await page.locator('#view').boundingBox();const x=b.x+b.width/2,y=b.y+b.height/2;
    await page.mouse.move(x,y);await page.mouse.down();await page.mouse.move(x+(request.dx||0),y+(request.dy||0),{steps:4});await page.mouse.up();
   }else if(action==='zoom'){
    await page.locator('#view').hover();await page.mouse.wheel(0,Number(value));
   }else if(action==='reload'){
    await page.reload();await page.waitForSelector('#view[data-ready="true"]');await page.evaluate(()=>document.fonts.ready);
   }else if(action!=='capture')throw Error('Unknown command');
   await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
   const file=path.join(out,String(++number).padStart(3,'0')+'-'+action+'.png');
   await page.screenshot({path:file,fullPage:true});
   console.log(JSON.stringify({ok:true,action,elapsed_ms:Math.round(performance.now()-start),screenshot:file,status:await page.locator('#status').innerText(),errors}));
  }catch(e){console.log(JSON.stringify({ok:false,request,error:String(e)}))}
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1});
