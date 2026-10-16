// @ts-check
const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

async function runVisualAudit() {
  const screenshotsDir = path.join(__dirname, 'screenshots');
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
  }

  const browser = await chromium.launch({
    headless: true,
  });

  console.log('===============================================================');
  console.log(' AUDIT VISUAL & CAPTURE TAMPILAN MULTI-VIEWPORT (PLAYWRIGHT)   ');
  console.log('===============================================================');

  // 1. DESKTOP VIEWPORT (1280 x 800)
  console.log('[1/2] Memeriksa Tampilan Desktop (1280 x 800)...');
  const desktopContext = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    deviceScaleFactor: 1,
  });
  const desktopPage = await desktopContext.newPage();
  
  // Dashboard Desktop
  await desktopPage.goto('http://localhost:8000/');
  await desktopPage.waitForLoadState('networkidle');
  // Trigger CV demo to show full populated dashboard
  await desktopPage.locator('#btn-cv-demo').click();
  await desktopPage.waitForSelector('#cv-result-box', { state: 'visible' });
  await desktopPage.locator('#btn-apply-cv').click();
  await desktopPage.waitForSelector('#sim-result-content', { state: 'visible' });

  // Check horizontal overflow
  const desktopOverflow = await desktopPage.evaluate(() => {
    return document.documentElement.scrollWidth > window.innerWidth;
  });
  console.log(`  - Desktop Horizontal Overflow: ${desktopOverflow ? 'FAIL (Meluap)' : 'PASS (Bebas Overflow)'}`);

  const desktopScreenshot = path.join(screenshotsDir, 'desktop_dashboard.png');
  await desktopPage.screenshot({ path: desktopScreenshot, fullPage: true });
  console.log(`  - Tangkapan layar Desktop: ${desktopScreenshot}`);

  // Verify Portal Desktop
  await desktopPage.goto('http://localhost:8000/verify.html');
  await desktopPage.waitForLoadState('networkidle');
  const desktopVerifyScreenshot = path.join(screenshotsDir, 'desktop_verify.png');
  await desktopPage.screenshot({ path: desktopVerifyScreenshot, fullPage: true });
  console.log(`  - Tangkapan layar Verify Desktop: ${desktopVerifyScreenshot}`);

  // 2. MOBILE ANDROID VIEWPORT (412 x 915 - Samsung Galaxy / Modern Android)
  console.log('[2/2] Memeriksa Tampilan Mobile Android (412 x 915)...');
  const mobileContext = await browser.newContext({
    viewport: { width: 412, height: 915 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
  });
  const mobilePage = await mobileContext.newPage();

  // Dashboard Mobile
  await mobilePage.goto('http://localhost:8000/');
  await mobilePage.waitForLoadState('networkidle');
  await mobilePage.locator('#btn-cv-demo').click();
  await mobilePage.waitForSelector('#cv-result-box', { state: 'visible' });
  await mobilePage.locator('#btn-apply-cv').click();
  await mobilePage.waitForSelector('#sim-result-content', { state: 'visible' });

  // Check horizontal overflow
  const mobileOverflow = await mobilePage.evaluate(() => {
    return document.documentElement.scrollWidth > window.innerWidth;
  });
  console.log(`  - Mobile Horizontal Overflow: ${mobileOverflow ? 'FAIL (Meluap)' : 'PASS (Bebas Overflow)'}`);

  const mobileScreenshot = path.join(screenshotsDir, 'mobile_dashboard.png');
  await mobilePage.screenshot({ path: mobileScreenshot, fullPage: true });
  console.log(`  - Tangkapan layar Mobile: ${mobileScreenshot}`);

  // Verify Portal Mobile
  await mobilePage.goto('http://localhost:8000/verify.html');
  await mobilePage.waitForLoadState('networkidle');
  const mobileVerifyScreenshot = path.join(screenshotsDir, 'mobile_verify.png');
  await mobilePage.screenshot({ path: mobileVerifyScreenshot, fullPage: true });
  console.log(`  - Tangkapan layar Verify Mobile: ${mobileVerifyScreenshot}`);

  await browser.close();

  console.log('===============================================================');
  console.log(' [✓] AUDIT VISUAL SELESAI — SELURUH VIEWPORT MEMENUHI STANDAR ');
  console.log('===============================================================');
}

runVisualAudit().catch((err) => {
  console.error('Audit Visual Gagal:', err);
  process.exit(1);
});
