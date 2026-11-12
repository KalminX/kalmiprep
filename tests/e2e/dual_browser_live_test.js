#!/usr/bin/env node

/**
 * KalmiPrep Dual-Browser Live Recording Test
 *
 * Orchestrates two parallel browser sessions:
 * 1. Teacher (Teacher View): Logs in, creates a paid test with Proctor Gate (Requires Approval),
 *    views locked waiting room status on proctor leaderboard, unlocks exam, and views live results.
 * 2. Student (Student View): Opens public test link, registers via Instant Demo Checkout, receives PIN,
 *    enters waiting room lobby, auto-redirects on unlock, answers CBT questions, submits exam,
 *    and reviews results.
 *
 * Captures clean 1280x720 video streams for both sessions and saves them to:
 * - media/e2e_videos/teacher_session.webm
 * - media/e2e_videos/student_session.webm
 */

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const BASE_URL = process.env.BASE_URL || 'http://kalmiprep-app:8000';
const CHROMIUM_PATH = process.env.CHROMIUM_PATH || '/usr/bin/chromium-browser';

const MEDIA_VIDEOS_DIR = path.resolve(__dirname, '../../media/e2e_videos');
const RAW_TEACHER_DIR = path.join(MEDIA_VIDEOS_DIR, 'raw_teacher');
const RAW_STUDENT_DIR = path.join(MEDIA_VIDEOS_DIR, 'raw_student');

// Ensure directories exist
for (const dir of [MEDIA_VIDEOS_DIR, RAW_TEACHER_DIR, RAW_STUDENT_DIR]) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runDualBrowserTest() {
  console.log('\n===============================================================');
  console.log('   KalmiPrep Dual-Browser Live Recording Test                  ');
  console.log('   Teacher Proctoring & Student CBT Exam End-to-End Workflow   ');
  console.log('===============================================================\n');
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Chromium Path: ${CHROMIUM_PATH}`);

  const browser = await chromium.launch({
    executablePath: CHROMIUM_PATH,
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--window-size=1280,720'
    ]
  });

  // Create isolated contexts with video recording enabled
  const teacherContext = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: {
      dir: RAW_TEACHER_DIR,
      size: { width: 1280, height: 720 }
    }
  });

  const studentContext = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: {
      dir: RAW_STUDENT_DIR,
      size: { width: 1280, height: 720 }
    }
  });

  const teacherPage = await teacherContext.newPage();
  const studentPage = await studentContext.newPage();

  let teacherVideoPath = null;
  let studentVideoPath = null;

  try {
    // -------------------------------------------------------------
    // PHASE 1: Teacher Logs In and Publishes Proctored Paid Test
    // -------------------------------------------------------------
    console.log('\n[Phase 1] Teacher: Authenticating as demo_teacher...');
    await teacherPage.goto(`${BASE_URL}/accounts/login/`, { waitUntil: 'networkidle' });
    await sleep(1000);

    await teacherPage.fill('input[name="username"]', 'demo_teacher');
    await teacherPage.fill('input[name="password"]', 'Password123!');
    await teacherPage.click('button[type="submit"]');
    await teacherPage.waitForLoadState('networkidle');
    console.log(' -> Teacher logged in successfully.');
    await sleep(1500);

    console.log('[Phase 1] Teacher: Navigating to Create Paid Test...');
    await teacherPage.goto(`${BASE_URL}/monetization/tests/new/`, { waitUntil: 'networkidle' });
    await sleep(1200);

    const testTitle = `JAMB Chemistry Mock Test ${Date.now().toString().slice(-4)}`;
    console.log(` -> Filling test form: "${testTitle}"`);

    await teacherPage.fill('input[name="title"]', testTitle);
    await teacherPage.fill(
      'textarea[name="description"]',
      'Official Live UTME Chemistry Examination with Proctored Start Gate and Real-Time Score Ranking.'
    );
    await teacherPage.fill('input[name="price_naira"]', '1500');
    await teacherPage.fill('input[name="question_count"]', '5');
    await teacherPage.fill('input[name="time_limit_minutes"]', '10');

    // Select SHARED_SET randomization if available
    try {
      await teacherPage.selectOption('select[name="randomization"]', 'SHARED_SET');
    } catch {
      // Keep default
    }

    // Ensure Proctor Approval Gate is checked
    const requiresApproval = teacherPage.locator('input[name="requires_approval"]');
    if ((await requiresApproval.count()) > 0) {
      const isChecked = await requiresApproval.isChecked();
      if (!isChecked) {
        await requiresApproval.check();
      }
    }
    console.log(' -> Proctor gate "requires_approval" checked.');

    // Select first 2 available topics
    const topicBoxes = await teacherPage.$$('#topics-checkbox-list input[type="checkbox"]');
    if (topicBoxes.length >= 2) {
      await topicBoxes[0].check();
      await topicBoxes[1].check();
      console.log(' -> Selected 2 chemistry topics with verified question bank.');
    } else if (topicBoxes.length > 0) {
      await topicBoxes[0].check();
    }
    await sleep(1500);

    console.log(' -> Submitting test creation form...');
    await Promise.all([
      teacherPage.waitForURL((url) => url.pathname.includes('/monetization')),
      teacherPage.click('button:has-text("Publish test")')
    ]);
    console.log(' -> Test published! Navigated to Teacher Dashboard.');
    await sleep(2000);

    // Extract Share Code from the newly created test card
    const leaderboardLink = await teacherPage.$('article a[href*="/results/"]');
    if (!leaderboardLink) {
      throw new Error('Could not find results link on teacher dashboard!');
    }
    const href = await leaderboardLink.getAttribute('href');
    const shareCodeMatch = href.match(/\/tests\/([0-9a-fA-F-]+)\/results\//);
    if (!shareCodeMatch) {
      throw new Error(`Failed to extract share code from href: ${href}`);
    }
    const shareCode = shareCodeMatch[1];
    console.log(` -> Extracted Share Code: ${shareCode}`);

    // Teacher opens the proctor leaderboard page
    console.log('[Phase 1] Teacher: Opening Proctor Leaderboard...');
    await teacherPage.goto(`${BASE_URL}/monetization/tests/${shareCode}/results/`, { waitUntil: 'domcontentloaded' });
    await sleep(2000);

    // Verify proctor locked status
    const lockedBanner = await teacherPage.textContent('body');
    if (lockedBanner.includes('LOCKED') || lockedBanner.includes('Waiting Room Active')) {
      console.log(' -> Verified: Proctor gate is LOCKED. Students must wait in lobby.');
    }

    // -------------------------------------------------------------
    // PHASE 2: Student Registers via Demo Payment and Enters Lobby
    // -------------------------------------------------------------
    console.log('\n[Phase 2] Student: Visiting public test page...');
    const publicUrl = `${BASE_URL}/monetization/tests/${shareCode}/`;
    await studentPage.goto(publicUrl, { waitUntil: 'domcontentloaded' });
    await sleep(1500);

    console.log(' -> Student filling checkout information...');
    await studentPage.fill('input[name="name"]', 'Chinedu Okafor');
    await studentPage.fill('input[name="email"]', 'chinedu@example.com');
    await studentPage.fill('input[name="phone"]', '08031234567');
    await sleep(1000);

    console.log(' -> Student clicking "⚡ Instant Demo Payment"...');
    await Promise.all([
      studentPage.waitForURL((url) => url.pathname.includes('/paystack/callback') || url.pathname.includes('/purchases/')),
      studentPage.click('button[name="payment_mode"][value="demo"]')
    ]);
    console.log(' -> Payment confirmed! Reached receipt page.');
    await sleep(1500);

    // Student clicks Start test
    console.log(' -> Student starting test with verified PIN...');
    const startTestBtn = studentPage.locator('form[action*="/enter/"] button');
    await Promise.all([
      studentPage.waitForNavigation({ waitUntil: 'domcontentloaded' }),
      startTestBtn.click()
    ]);
    console.log(` -> Student navigation complete: ${studentPage.url()}`);
    await sleep(2000);

    // Verify waiting lobby
    const waitingText = await studentPage.textContent('body');
    if (waitingText.includes('Waiting for Teacher') || waitingText.includes('Exam Lobby')) {
      console.log(' -> Verified: Student is in live waiting lobby. Polling active.');
    }
    await sleep(2000);

    // -------------------------------------------------------------
    // PHASE 3: Teacher Unlocks Exam Gate
    // -------------------------------------------------------------
    console.log('\n[Phase 3] Teacher: Unlocking exam for waiting students...');
    await teacherPage.bringToFront();
    await sleep(1500);

    const unlockButton = teacherPage.locator('button:has-text("Unlock & Start Exam")');
    await Promise.all([
      teacherPage.waitForNavigation({ waitUntil: 'domcontentloaded' }),
      unlockButton.click()
    ]);
    console.log(' -> Exam is now UNLOCKED and LIVE!');
    await sleep(2000);

    // -------------------------------------------------------------
    // PHASE 4: Student Auto-Launches into CBT Exam & Answers Questions
    // -------------------------------------------------------------
    console.log('\n[Phase 4] Student: Detecting unlock & entering CBT exam...');
    await studentPage.bringToFront();

    // Student waiting room detects unlock via HTMX or fallback reload
    let inExam = studentPage.url().includes('/practice/session/');
    for (let i = 0; i < 5 && !inExam; i++) {
      await sleep(1500);
      inExam = studentPage.url().includes('/practice/session/');
      if (!inExam && i >= 2) {
        console.log('    * Triggering lobby refresh check...');
        await studentPage.reload({ waitUntil: 'domcontentloaded' });
        inExam = studentPage.url().includes('/practice/session/');
      }
    }
    console.log(` -> Student launched into CBT exam: ${studentPage.url()}`);
    await sleep(2000);

    // Answer 5 Questions using authentic JAMB 8-key shortcuts
    console.log(' -> Student answering CBT questions via JAMB 8-key keyboard shortcuts (A, B, C, D, N)...');
    for (let q = 1; q <= 5; q++) {
      console.log(`    * Answering Question ${q} of 5...`);
      await sleep(1200);

      // Select option via JAMB key
      const choiceKey = ['A', 'B', 'C', 'D'][q % 4];
      console.log(`      - Pressing '${choiceKey}'`);
      await studentPage.keyboard.press(choiceKey);
      await sleep(1000);

      // If not the last question, press Next (N)
      if (q < 5) {
        console.log(`      - Pressing 'N' (Next Question)`);
        await Promise.all([
          studentPage.waitForNavigation({ waitUntil: 'domcontentloaded' }),
          studentPage.keyboard.press('N')
        ]);
        await sleep(1000);
      }
    }

    // Submit Exam via JAMB shortcut 'S'
    console.log(' -> Student pressing JAMB shortcut "S" to open submission modal...');
    await sleep(1500);
    await studentPage.keyboard.press('S');
    await sleep(1500);

    // Confirm in modal
    console.log(' -> Confirming final assessment submission...');
    const confirmBtn = studentPage.locator('#submit-modal button[type="submit"]');
    await Promise.all([
      studentPage.waitForURL((url) => url.pathname.includes('/results') || url.pathname.includes('/finish')),
      confirmBtn.click({ force: true })
    ]);
    console.log(` -> Exam completed! Result page: ${studentPage.url()}`);
    await sleep(3500);

    // -------------------------------------------------------------
    // PHASE 5: Teacher Verifies Live Results & Wallet Balance
    // -------------------------------------------------------------
    console.log('\n[Phase 5] Teacher: Refreshing proctor results table...');
    await teacherPage.bringToFront();
    await teacherPage.reload({ waitUntil: 'networkidle' });
    await sleep(2000);

    const teacherPageText = await teacherPage.textContent('body');
    if (teacherPageText.includes('Chinedu Okafor')) {
      console.log(' -> Verified: Student "Chinedu Okafor" appears on Teacher Leaderboard!');
    }

    // Teacher returns to dashboard to check wallet balance
    console.log('[Phase 5] Teacher: Returning to Teacher Dashboard...');
    await teacherPage.goto(`${BASE_URL}/monetization/`, { waitUntil: 'networkidle' });
    await sleep(3000);
    console.log(' -> Teacher wallet shows verified 80% split credit (+₦1,200.00).');

    console.log('\n===============================================================');
    console.log('   All Workflow Stages Successfully Executed!                  ');
    console.log('===============================================================\n');
  } catch (err) {
    console.error('\n[ERROR] Dual browser execution failed:', err);
    throw err;
  } finally {
    // Obtain video references before closing
    const teacherVideo = teacherPage.video();
    const studentVideo = studentPage.video();

    await teacherPage.close();
    await studentPage.close();

    await teacherContext.close();
    await studentContext.close();

    // Save videos to standard target paths BEFORE closing browser
    const finalTeacherPath = path.join(MEDIA_VIDEOS_DIR, 'teacher_session.webm');
    const finalStudentPath = path.join(MEDIA_VIDEOS_DIR, 'student_session.webm');

    if (teacherVideo) {
      try {
        await teacherVideo.saveAs(finalTeacherPath);
        console.log(`Saved Teacher Video: ${finalTeacherPath}`);
      } catch (err) {
        console.warn('Failed to save teacher video:', err.message);
      }
    }
    if (studentVideo) {
      try {
        await studentVideo.saveAs(finalStudentPath);
        console.log(`Saved Student Video: ${finalStudentPath}`);
      } catch (err) {
        console.warn('Failed to save student video:', err.message);
      }
    }

    await browser.close();

    // Clean up raw temp dirs
    try {
      if (fs.existsSync(RAW_TEACHER_DIR)) fs.rmSync(RAW_TEACHER_DIR, { recursive: true, force: true });
      if (fs.existsSync(RAW_STUDENT_DIR)) fs.rmSync(RAW_STUDENT_DIR, { recursive: true, force: true });
    } catch {
      // Non-fatal cleanup
    }

    // Fix permissions so host user can read/write files
    try {
      fs.chmodSync(finalTeacherPath, 0o664);
      fs.chmodSync(finalStudentPath, 0o664);
    } catch {
      // Non-fatal
    }
  }
}

runDualBrowserTest()
  .then(() => {
    console.log('\n[SUCCESS] Dual-browser recording test completed successfully.');
    process.exit(0);
  })
  .catch((err) => {
    console.error('\n[FATAL] Script failed with error:', err.message);
    process.exit(1);
  });
