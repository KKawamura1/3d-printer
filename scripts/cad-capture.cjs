/** Real Chromium screenshots for BrickCAD viewers; not a manual visual review. */
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {createHash} = require('node:crypto');
const {launchBrowser} = require('./browser-runtime.cjs');

(async () => {
  const model = path.resolve(process.argv[2]);
  const output = path.resolve(process.argv[3]);
  await fs.mkdir(output, {recursive: true});
  const browser = await launchBrowser();
  const records = [];
  try {
    const page = await browser.newPage({viewport: {width: 1200, height: 850}});
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(pathToFileURL(path.join(model, 'viewer.html')).href);
    await page.waitForSelector('#view[data-ready="true"]', {timeout: 30000});
    await page.evaluate(() => document.fonts.ready);
    const cameras = await page.locator('#camera option').evaluateAll(opts => opts.map(x => x.value));
    for (const [camera, name] of [
      ['perspective', '01-perspective'], ['top', '02-top'],
      ['underside', '03-underside'], ['section', '04-section']
    ]) {
      if (!cameras.includes(camera)) continue;
      await page.selectOption('#camera', camera);
      if (camera === 'section' && await page.locator('#mode option[value="section"]').count()) {
        await page.selectOption('#mode', 'section');
      }
      await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
      const pixels = await page.locator('#view').evaluate(canvas => {
        const gl = canvas.getContext('webgl');
        if (!gl) throw Error('No WebGL context');
        const data = new Uint8Array(canvas.width * canvas.height * 4);
        gl.readPixels(0, 0, canvas.width, canvas.height, gl.RGBA, gl.UNSIGNED_BYTE, data);
        let red = 0;
        for (let i = 0; i < data.length; i += 4)
          if (data[i] > 70 && data[i] > data[i+1] * 1.6 && data[i] > data[i+2] * 1.5) red++;
        return red;
      });
      if (pixels < 1000) throw Error(name + ' blank (' + pixels + ' pixels)');
      const png = await page.screenshot({path: path.join(output, name + '.png'), fullPage: true});
      records.push({view: name, pixels, sha256: createHash('sha256').update(png).digest('hex')});
      if (camera === 'section' && await page.locator('#mode option[value="single"]').count()) {
        await page.selectOption('#mode', 'single');
      }
    }
    if (!records.length || errors.length) throw Error('Capture failed: ' + errors.join('; '));
    await fs.writeFile(path.join(output, 'capture.json'),
      JSON.stringify({automated_passed: true, visual_review_performed: false, captures: records}, null, 2) + '\n');
    console.log('CAPTURED', records.map(x => x.view).join(', '));
  } finally { await browser.close(); }
})().catch(err => { console.error(err); process.exitCode = 1; });
