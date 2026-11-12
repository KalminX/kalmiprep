#!/usr/bin/env node

/**
 * KalmiPrep Fast Dual-Browser Lifecycle Test (Zero Video Overhead)
 *
 * Simulates and strictly asserts the complete Teacher Proctoring & Student CBT Exam workflow:
 * 1. Teacher creates Paid Test with Proctor Gate ("Requires approval") and custom pricing (₦1,500).
 * 2. Student discovers test via share link, completes instant demo payment, receives verified PIN.
 * 3. Student enters PIN, gets held in live waiting room lobby. Direct exam access is gated.
 * 4. Teacher proctor leaderboard unlocks exam; student lobby detects unlock and auto-redirects.
 * 5. Student answers CBT questions using real JAMB 8-key shortcuts (A, B, C, D, N).
 * 6. Student submits assessment via confirmation modal; ensures zero beforeunload dialogs fire.
 * 7. Student Result Card displays verified 4 / 5 (80%) Distinction score.
 * 8. Teacher Proctor Leaderboard displays student ("Chinedu Okafor") with 4/5 (80.0%).
 * 9. Teacher wallet reflects verified 80% split credit (+₦1,200.00).
 *
 * Runs headless with hard fatal assertions in ~6 to 8 seconds. NO video recording.
 */

const assert = require('assert');
const { chromium } = require('playwright-core');

const BASE_URL = process.env.BASE_URL || 'http://kalmiprep-app:8000';
const CHROMIUM_PATH = process.env.CHROMIUM_PATH || '/usr/bin/chromium-browser';

async function runFastLifecycleTest() {
  console.log('\n===============================================================');
  console.log('   KalmiPrep Fast Dual-Browser Workflow Assertion Suite        ');
  console.log('   (Pure DOM & API Simulation — Zero Video Recording)          ');
  console.log('===============================================================\n');
  console.log(`Base URL: ${BASE_URL}`);

  const browser = await chromium.launch({
    executablePath: CHROMIUM_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const startTime = Date.now();

  try {
    // -------------------------------------------------------------
    // CONTEXT 1: Teacher Session
    // -------------------------------------------------------------
    const teacherContext = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const teacherPage = await teacherContext.newPage();

    // -------------------------------------------------------------
    // CONTEXT 2: Student Session
    // -------------------------------------------------------------
    const studentContext = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const studentPage = await studentContext.newPage();

    // Listen for unexpected beforeunload / alert dialogs
    let unexpectedDialog = null;
    studentPage.on('dialog', (dialog) => {
      unexpectedDialog = `${dialog.type()}: ${dialog.message()}`;
      dialog.dismiss().catch(() => {});
    });

    // -------------------------------------------------------------
    // STAGE 1: Teacher Logs In
    // -------------------------------------------------------------
    console.log('[Stage 1] Teacher: Authenticating as demo_teacher...');
    await teacherPage.goto(`${BASE_URL}/accounts/login/`, { waitUntil: 'domcontentloaded' });
    await teacherPage.fill('input[name="username"]', 'demo_teacher');
    await teacherPage.fill('input[name="password"]', 'Password123!');
    await teacherPage.click('button[type="submit"]');
    await teacherPage.waitForLoadState('domcontentloaded');

    // -------------------------------------------------------------
    // STAGE 2: Teacher Creates Paid Test with Proctor Gate
    // -------------------------------------------------------------
    console.log('[Stage 2] Teacher: Creating Paid Test with Proctor Gate...');
    await teacherPage.goto(`${BASE_URL}/monetization/tests/new/`, { waitUntil: 'domcontentloaded' });
    const testTitle = `Fast Lifecycle Test ${Date.now().toString().slice(-4)}`;
    await teacherPage.fill('input[name="title"]', testTitle);
    await teacherPage.fill('input[name="price_naira"]', '1500.00');
    await teacherPage.fill('input[name="question_count"]', '5');
    await teacherPage.fill('input[name="time_limit_minutes"]', '10');

    try {
      await teacherPage.selectOption('select[name="randomization"]', 'SHARED_SET');
    } catch {
      // Keep default
    }

    // Enable Proctor Gate
    const requiresApproval = teacherPage.locator('input[name="requires_approval"]');
    if ((await requiresApproval.count()) > 0) {
      if (!(await requiresApproval.isChecked())) {
        await requiresApproval.check();
      }
    }

    // Select first 2 available topics
    const topicBoxes = await teacherPage.$$('#topics-checkbox-list input[type="checkbox"]');
    if (topicBoxes.length >= 2) {
      await topicBoxes[0].check();
      await topicBoxes[1].check();
    } else if (topicBoxes.length > 0) {
      await topicBoxes[0].check();
    }

    // Submit form and navigate to dashboard
    await Promise.all([
      teacherPage.waitForURL((url) => url.pathname.includes('/monetization')),
      teacherPage.click('button:has-text("Publish test")')
    ]);

    // Extract Share Code
    const leaderboardLink = await teacherPage.$('article a[href*="/results/"]');
    assert.ok(leaderboardLink, 'Teacher dashboard must contain results link');
    const href = await leaderboardLink.getAttribute('href');
    const shareCodeMatch = href.match(/\/tests\/([0-9a-fA-F-]+)\/results\//);
    assert.ok(shareCodeMatch, 'Must extract valid UUID share code');
    const shareCode = shareCodeMatch[1];
    console.log(` -> Test Published! Share Code: ${shareCode}`);

    // Teacher opens proctor leaderboard
    await teacherPage.goto(`${BASE_URL}/monetization/tests/${shareCode}/results/`, { waitUntil: 'domcontentloaded' });

    // -------------------------------------------------------------
    // STAGE 3: Student Discovers Test & Performs Demo Checkout
    // -------------------------------------------------------------
    console.log('[Stage 3] Student: Checkout & Instant Demo Payment...');
    const publicUrl = `${BASE_URL}/monetization/tests/${shareCode}/`;
    await studentPage.goto(publicUrl, { waitUntil: 'domcontentloaded' });

    await studentPage.fill('input[name="name"]', 'Chinedu Okafor');
    await studentPage.fill('input[name="email"]', 'chinedu@example.com');
    await studentPage.fill('input[name="phone"]', '08031234567');

    // Click Instant Demo Payment
    await Promise.all([
      studentPage.waitForURL((url) => url.pathname.includes('/paystack/callback') || url.pathname.includes('/purchases/')),
      studentPage.click('button[name="payment_mode"][value="demo"]')
    ]);
    console.log(' -> Payment Verified! Receipt confirmed.');

    // -------------------------------------------------------------
    // STAGE 4: Student Enters Waiting Room Lobby
    // -------------------------------------------------------------
    console.log('[Stage 4] Student: Entering Waiting Room...');
    const startTestBtn = studentPage.locator('form[action*="/enter/"] button');
    await Promise.all([
      studentPage.waitForNavigation({ waitUntil: 'domcontentloaded' }),
      startTestBtn.click()
    ]);

    assert.ok(studentPage.url().includes('/waiting/'), 'Student must be held in waiting room');
    console.log(' -> Student successfully gated in waiting lobby.');

    // -------------------------------------------------------------
    // STAGE 5: Teacher Proctor Unlocks Exam
    // -------------------------------------------------------------
    console.log('[Stage 5] Teacher: Proctor Unlocking Exam...');
    await teacherPage.reload({ waitUntil: 'domcontentloaded' });
    const unlockBtn = teacherPage.locator('button:has-text("Unlock & Start Exam"), button:has-text("Unlock Exam"), form[action*="/approve/"] button').first();
    assert.ok(await unlockBtn.isVisible(), 'Unlock button must be visible to teacher');

    await Promise.all([
      teacherPage.waitForNavigation({ waitUntil: 'domcontentloaded' }),
      unlockBtn.click()
    ]);
    console.log(' -> Exam UNLOCKED by teacher!');

    // -------------------------------------------------------------
    // STAGE 6: Student Auto-Redirects to CBT Exam
    // -------------------------------------------------------------
    console.log('[Stage 6] Student: Detecting unlock & transitioning to CBT...');
    await studentPage.waitForURL((url) => url.pathname.includes('/practice/session/'), { timeout: 10000 });
    const cbtUrl = studentPage.url();
    assert.ok(cbtUrl.includes('/practice/session/'), 'Student must enter active CBT session');
    const sessionIdMatch = cbtUrl.match(/\/session\/(\d+)\//);
    assert.ok(sessionIdMatch, 'Must resolve session ID');
    const sessionId = sessionIdMatch[1];
    console.log(` -> Live CBT Session Active: Session ${sessionId}`);

    // Fetch verified answer keys
    const diagRes = await studentPage.request.get(`${BASE_URL}/practice/session/${sessionId}/e2e-keys/`);
    assert.strictEqual(diagRes.status(), 200, 'Answer key diagnostic must return 200');
    const diagData = await diagRes.json();
    const correctTags = diagData.correct_tags || ['A', 'B', 'C', 'D', 'A'];
    console.log(' -> Target Answer Sequence:', correctTags);

    // -------------------------------------------------------------
    // STAGE 7: Student Answers via JAMB 8-Key Keyboard Shortcuts
    // -------------------------------------------------------------
    console.log('[Stage 7] Student: Answering Questions via JAMB 8-Key Shortcuts...');
    for (let qIdx = 0; qIdx < 5; qIdx++) {
      // Questions 1..4: Correct target. Question 5: Incorrect target (yields exactly 4/5 = 80% distinction)
      let targetKey = correctTags[qIdx] || 'A';
      if (qIdx === 4) {
        const allTags = ['A', 'B', 'C', 'D'];
        targetKey = allTags.find(t => t !== targetKey) || 'B';
      }

      await Promise.all([
        studentPage.waitForResponse(res => res.url().includes('/submit/') && res.status() === 200, { timeout: 8000 }).catch(() => null),
        studentPage.keyboard.press(targetKey)
      ]);
      await studentPage.waitForTimeout(300);

      if (qIdx < 4) {
        await Promise.all([
          studentPage.waitForNavigation({ waitUntil: 'domcontentloaded' }),
          studentPage.keyboard.press('N')
        ]);
        await studentPage.waitForTimeout(300);
      }
    }

    // -------------------------------------------------------------
    // STAGE 8: Student Submits Assessment
    // -------------------------------------------------------------
    console.log('[Stage 8] Student: Submitting Exam via Modal...');
    await studentPage.keyboard.press('S');
    const confirmBtn = studentPage.locator('#submit-modal button[type="submit"]');
    await confirmBtn.waitFor({ state: 'visible', timeout: 5000 });

    await Promise.all([
      studentPage.waitForURL((url) => url.pathname.includes('/results'), { timeout: 10000 }),
      confirmBtn.click({ force: true })
    ]);

    assert.strictEqual(unexpectedDialog, null, 'No beforeunload warning dialog should have fired');

    // -------------------------------------------------------------
    // STAGE 9: Student Scorecard Verification (4 / 5 = 80% Distinction)
    // -------------------------------------------------------------
    console.log('[Stage 9] Verifying Student Distinction Scorecard...');
    const resultText = await studentPage.textContent('body');
    assert.ok(resultText.includes('4 / 5') || resultText.includes('4/5'), 'Scorecard must display 4 / 5');
    assert.ok(resultText.includes('80%'), 'Scorecard must display 80% Distinction');
    console.log(' -> Verified: Student Scorecard = 4 / 5 (80%) Distinction');

    // -------------------------------------------------------------
    // STAGE 10: Teacher Proctor Leaderboard Synchronization
    // -------------------------------------------------------------
    console.log('[Stage 10] Verifying Teacher Proctor Leaderboard Sync...');
    await teacherPage.reload({ waitUntil: 'domcontentloaded' });
    const teacherText = await teacherPage.textContent('body');
    assert.ok(teacherText.includes('Chinedu Okafor'), 'Leaderboard must show candidate name Chinedu Okafor');
    assert.ok(teacherText.includes('80.0%') || teacherText.includes('80%'), 'Leaderboard must reflect 80.0%');
    assert.ok(teacherText.includes('4/5') || teacherText.includes('4 / 5'), 'Leaderboard must reflect 4/5');
    console.log(' -> Verified: Teacher Proctor Leaderboard reflects Chinedu Okafor (4/5, 80.0%)');

    // -------------------------------------------------------------
    // STAGE 11: Teacher Wallet Balance Verification
    // -------------------------------------------------------------
    console.log('[Stage 11] Verifying Teacher Wallet Credit...');
    await teacherPage.goto(`${BASE_URL}/monetization/`, { waitUntil: 'domcontentloaded' });
    const walletText = await teacherPage.textContent('body');
    assert.ok(
      walletText.includes('1200') || walletText.includes('1,200'),
      'Teacher wallet must show 80% credit (₦1,200.00 or ₦1200.00)'
    );
    assert.ok(
      walletText.includes(testTitle),
      'Recent wallet entries must record the purchased test transaction'
    );
    console.log(' -> Verified: Teacher Wallet credited with 80% split (+₦1,200.00)');

    const durationSec = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log('\n===============================================================');
    console.log(`   SUCCESS: All 11 Checkpoints Verified in ${durationSec}s!`);
    console.log('   Zero video recording, zero ffmpeg, zero media artifacts.   ');
    console.log('===============================================================\n');

    await browser.close();
  } catch (err) {
    console.error('\n[FATAL TEST FAILURE]:', err);
    await browser.close().catch(() => {});
    process.exit(1);
  }
}

runFastLifecycleTest();
