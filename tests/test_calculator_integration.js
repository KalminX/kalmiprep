/**
 * DOM-level integration tests for the scientific calculator (jsdom).
 * Exercises the real store.js and the real keypad markup from templates/components/calculator_modal.html.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const root = path.join(__dirname, '..');
const read = (p) => fs.readFileSync(path.join(root, p), 'utf8');
const STORE = read('static/js/store.js');
const ENGINE = read('static/js/calculator/engine.js');
const MEMENTO = read('static/js/calculator/memento.js');
const CONTROLLER = read('static/js/calculator/controller.js');
const MODAL_HTML = read('templates/components/calculator_modal.html')
  .replace(/\{#[\s\S]*?#\}/g, '')
  .replace(/\{%[\s\S]*?%\}/g, '')
  .replace(/<script>[\s\S]*?<\/script>/g, '')
  .replace(/<link[^>]*>/g, '');

const MATHJS = read('static/vendor/mathjs/math.min.js');

let failures = 0;
function test(name, fn) {
  try {
    fn();
    console.log(`✓ PASS: ${name}`);
  } catch (err) {
    failures += 1;
    console.error(`✗ FAIL: ${name}\n`, err);
  }
}

function makePage({ calculator = true, savedMemento = null } = {}) {
  const dom = new JSDOM(`<!doctype html><html><body>
    <form id="answer-form">
      <label class="cbt-option-item">
        <span>A</span>
        <input type="radio" name="option_id" value="1" checked>
      </label>
    </form>
    <div id="timer">12:34</div>
    ${calculator ? MODAL_HTML : ''}
  </body></html>`, {
    url: 'https://kalmiprep.test/practice/session/1/',
    runScripts: 'outside-only',
    pretendToBeVisual: true
  });
  const { window } = dom;
  if (savedMemento) {
    window.localStorage.setItem('kalmiprep_calc_memento', JSON.stringify(savedMemento));
  }
  window.eval(MATHJS);
  if (calculator) {
    window.eval(ENGINE);
    window.eval(MEMENTO);
    window.eval(CONTROLLER);
  }
  window.eval(STORE);
  return window;
}

console.log('--- RUNNING CALCULATOR INTEGRATION (JSDOM) TESTS ---');

test('Page WITHOUT the calculator modal: toggle, open and Alt+C are inert', () => {
  const win = makePage({ calculator: false });
  assert.strictEqual(win.document.getElementById('scientific-calculator-modal'), null);
  win.useKalmiStore.getState().toggleCalc();
  assert.strictEqual(win.useKalmiStore.getState().calc.isOpen, false);
});

test('Calculator starts closed even if a stale memento says it was open', () => {
  const win = makePage({ calculator: true, savedMemento: { isOpen: true, expression: '42', result: '42' } });
  const modal = win.document.getElementById('scientific-calculator-modal');
  assert.strictEqual(win.useKalmiStore.getState().calc.isOpen, false);
  assert.strictEqual(modal.classList.contains('hidden'), true);
  assert.strictEqual(modal.getAttribute('aria-hidden'), 'true');
});

test('Alt+C opens then closes the calculator; Escape closes it', () => {
  const win = makePage({ calculator: true });
  const modal = win.document.getElementById('scientific-calculator-modal');

  win.document.dispatchEvent(new win.KeyboardEvent('keydown', { key: 'c', altKey: true, bubbles: true }));
  assert.strictEqual(win.useKalmiStore.getState().calc.isOpen, true);
  assert.strictEqual(modal.classList.contains('hidden'), false);

  win.document.dispatchEvent(new win.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  assert.strictEqual(win.useKalmiStore.getState().calc.isOpen, false);
  assert.strictEqual(modal.classList.contains('hidden'), true);
});

test('Calc button path (toggleCalc) opens and closes', () => {
  const win = makePage({ calculator: true });
  const modal = win.document.getElementById('scientific-calculator-modal');
  win.useKalmiStore.getState().toggleCalc();
  assert.strictEqual(win.useKalmiStore.getState().calc.isOpen, true);
  assert.strictEqual(modal.classList.contains('hidden'), false);
  win.useKalmiStore.getState().closeCalc();
  assert.strictEqual(win.useKalmiStore.getState().calc.isOpen, false);
  assert.strictEqual(modal.classList.contains('hidden'), true);
});

test('Opening/closing leaves timer text, selected answer and form untouched', () => {
  const win = makePage({ calculator: true });
  const radio = win.document.querySelector('input[type=radio]');
  assert.strictEqual(radio.checked, true);
  assert.strictEqual(win.document.getElementById('timer').textContent, '12:34');

  win.useKalmiStore.getState().openCalc();
  win.useKalmiStore.getState().closeCalc();

  assert.strictEqual(radio.checked, true);
  assert.strictEqual(win.document.getElementById('timer').textContent, '12:34');
});

test('Every keypad button is type="button" (cannot submit a form)', () => {
  const win = makePage({ calculator: true });
  const btns = Array.from(win.document.querySelectorAll('#scientific-calculator-modal button'));
  assert(btns.length >= 35, `expected at least 35 buttons, got ${btns.length}`);
  for (const b of btns) {
    assert.strictEqual(b.getAttribute('type'), 'button', `button ${b.textContent} is not type="button"`);
  }
});

test('Keypad: 2 + 3 = evaluates to 5', () => {
  const win = makePage({ calculator: true });
  win.useKalmiStore.getState().openCalc();
  win.useKalmiStore.getState().clearCalc();

  win.useKalmiStore.getState().appendCalc('2');
  win.useKalmiStore.getState().appendCalc('+');
  win.useKalmiStore.getState().appendCalc('3');
  win.useKalmiStore.getState().evaluateCalc(true);

  assert.strictEqual(win.useKalmiStore.getState().calc.result, '5');
  assert.strictEqual(win.document.getElementById('calc-result-display').textContent, '5');
});

test('Keyboard typing works when calculator is open: 7 * 8 Enter evaluates to 56', () => {
  const win = makePage({ calculator: true });
  win.useKalmiStore.getState().openCalc();
  win.useKalmiStore.getState().clearCalc();

  win.document.dispatchEvent(new win.KeyboardEvent('keydown', { key: '7', bubbles: true }));
  win.document.dispatchEvent(new win.KeyboardEvent('keydown', { key: '*', bubbles: true }));
  win.document.dispatchEvent(new win.KeyboardEvent('keydown', { key: '8', bubbles: true }));
  win.document.dispatchEvent(new win.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));

  assert.strictEqual(win.useKalmiStore.getState().calc.result, '56');
  assert.strictEqual(win.document.getElementById('calc-result-display').textContent, '56');
});

test('Trigonometry respects DEG vs RAD', () => {
  const win = makePage({ calculator: true });
  win.useKalmiStore.getState().openCalc();

  // sin(30) in DEG
  win.useKalmiStore.getState().clearCalc();
  win.useKalmiStore.getState().setCalcAngleMode('DEG');
  win.useKalmiStore.getState().appendCalc('sin(');
  win.useKalmiStore.getState().appendCalc('30');
  win.useKalmiStore.getState().appendCalc(')');
  win.useKalmiStore.getState().evaluateCalc(true);
  assert.strictEqual(win.useKalmiStore.getState().calc.result, '0.5');

  // cos(90) in DEG is 0
  win.useKalmiStore.getState().clearCalc();
  win.useKalmiStore.getState().appendCalc('cos(');
  win.useKalmiStore.getState().appendCalc('90');
  win.useKalmiStore.getState().appendCalc(')');
  win.useKalmiStore.getState().evaluateCalc(true);
  assert.strictEqual(win.useKalmiStore.getState().calc.result, '0');

  // tan(90) in DEG is Math ERROR
  win.useKalmiStore.getState().clearCalc();
  win.useKalmiStore.getState().appendCalc('tan(');
  win.useKalmiStore.getState().appendCalc('90');
  win.useKalmiStore.getState().appendCalc(')');
  win.useKalmiStore.getState().evaluateCalc(true);
  assert.strictEqual(win.useKalmiStore.getState().calc.result, 'Math ERROR');
});

test('Auto-balancing unclosed parentheses: sin(30 evaluates to 0.5', () => {
  const win = makePage({ calculator: true });
  win.useKalmiStore.getState().openCalc();
  win.useKalmiStore.getState().setCalcAngleMode('DEG');
  win.useKalmiStore.getState().clearCalc();

  win.useKalmiStore.getState().appendCalc('sin(');
  win.useKalmiStore.getState().appendCalc('30');
  win.useKalmiStore.getState().evaluateCalc(true);
  assert.strictEqual(win.useKalmiStore.getState().calc.result, '0.5');
});

test('Ans recall and calculation chaining', () => {
  const win = makePage({ calculator: true });
  win.useKalmiStore.getState().openCalc();
  win.useKalmiStore.getState().clearCalc();

  // 10 + 5 = 15
  win.useKalmiStore.getState().appendCalc('10');
  win.useKalmiStore.getState().appendCalc('+');
  win.useKalmiStore.getState().appendCalc('5');
  win.useKalmiStore.getState().evaluateCalc(true);
  assert.strictEqual(win.useKalmiStore.getState().calc.result, '15');

  // Chaining: press + 5 -> 15 + 5 = 20
  win.useKalmiStore.getState().appendCalc('+');
  win.useKalmiStore.getState().appendCalc('5');
  win.useKalmiStore.getState().evaluateCalc(true);
  assert.strictEqual(win.useKalmiStore.getState().calc.result, '20');

  // Typing new digit clears and starts new calculation
  win.useKalmiStore.getState().appendCalc('8');
  assert.strictEqual(win.useKalmiStore.getState().calc.expression, '8');
});

test('Memory operations (M+, M-, MR, MC)', () => {
  const win = makePage({ calculator: true });
  win.useKalmiStore.getState().openCalc();
  win.useKalmiStore.getState().memoryClear();
  assert.strictEqual(win.useKalmiStore.getState().calc.memory, 0);

  // Set result to 25, then M+
  win.useKalmiStore.getState().clearCalc();
  win.useKalmiStore.getState().appendCalc('25');
  win.useKalmiStore.getState().evaluateCalc(true);
  win.useKalmiStore.getState().memoryAdd();
  assert.strictEqual(win.useKalmiStore.getState().calc.memory, 25);

  // M- 5 -> memory 20
  win.useKalmiStore.getState().clearCalc();
  win.useKalmiStore.getState().appendCalc('5');
  win.useKalmiStore.getState().evaluateCalc(true);
  win.useKalmiStore.getState().memorySubtract();
  assert.strictEqual(win.useKalmiStore.getState().calc.memory, 20);

  // Recall memory
  win.useKalmiStore.getState().clearCalc();
  win.useKalmiStore.getState().memoryRecall();
  assert.strictEqual(win.useKalmiStore.getState().calc.expression, '20');

  // MC clears
  win.useKalmiStore.getState().memoryClear();
  assert.strictEqual(win.useKalmiStore.getState().calc.memory, 0);
});

test('DEL removes last token or function; C clears everything', () => {
  const win = makePage({ calculator: true });
  win.useKalmiStore.getState().openCalc();

  win.useKalmiStore.getState().clearCalc();
  win.useKalmiStore.getState().appendCalc('123');
  win.useKalmiStore.getState().backspaceCalc();
  assert.strictEqual(win.useKalmiStore.getState().calc.expression, '12');

  win.useKalmiStore.getState().appendCalc('sin(');
  win.useKalmiStore.getState().backspaceCalc();
  assert.strictEqual(win.useKalmiStore.getState().calc.expression, '12');

  win.useKalmiStore.getState().clearCalc();
  assert.strictEqual(win.useKalmiStore.getState().calc.expression, '');
  assert.strictEqual(win.useKalmiStore.getState().calc.result, '0');
});

test('State persists in localStorage via GoF Memento pattern', () => {
  const win = makePage({ calculator: true });
  win.useKalmiStore.getState().openCalc();
  win.useKalmiStore.getState().clearCalc();
  win.useKalmiStore.getState().setCalcAngleMode('RAD');
  win.useKalmiStore.getState().appendCalc('42');
  win.useKalmiStore.getState().evaluateCalc(true);

  const raw = win.localStorage.getItem('kalmiprep_calc_memento');
  assert(raw, 'memento must be written to localStorage');
  const saved = JSON.parse(raw);
  assert.strictEqual(saved.angleMode, 'RAD');
  assert.strictEqual(saved.result, '42');
  assert.strictEqual(saved.isOpen, false); // memento strictly saves closed state
});

console.log(failures === 0 ? '--- ALL CALCULATOR INTEGRATION TESTS PASSED ---' : `--- ${failures} TEST(S) FAILED ---`);
process.exit(failures === 0 ? 0 : 1);
