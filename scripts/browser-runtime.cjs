/** Standard Playwright, with an optional bundled Linux browser for restricted runners. */
const fs=require('node:fs');
const path=require('node:path');
const zlib=require('node:zlib');
const {execFileSync}=require('node:child_process');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
async function launchBrowser(){
 const flags=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'];
 if(!process.env.BRICK_CHROMIUM_PACKAGE)return chromium.launch({headless:true,args:flags});
 const entry=path.resolve(process.env.BRICK_CHROMIUM_PACKAGE);
 const bin=path.resolve(path.dirname(entry),'../bin');
 const out=path.resolve('build/browser-runtime');
 fs.mkdirSync(out,{recursive:true});
 for(const name of ['chromium','fonts.tar','swiftshader.tar']){
  const destination=path.join(out,name);
  if(fs.existsSync(destination)&&fs.statSync(destination).size>0)continue;
  fs.writeFileSync(destination,zlib.brotliDecompressSync(fs.readFileSync(path.join(bin,name+'.br'))));
  if(name.endsWith('.tar'))execFileSync('tar',['--no-same-owner','--no-same-permissions','-xf',destination,'-C',out]);
  else fs.chmodSync(destination,0o700);
 }
 process.env.FONTCONFIG_PATH=path.join(out,'fonts');
 process.env.LD_LIBRARY_PATH=out+':'+(process.env.LD_LIBRARY_PATH||'');
 // Avoid the package's broad flags that disable web security and site isolation.
 return chromium.launch({headless:true,executablePath:path.join(out,'chromium'),args:[...flags,'--single-process','--no-zygote']});
}
module.exports={launchBrowser};
