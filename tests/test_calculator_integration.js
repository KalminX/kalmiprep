/**
 * DOM-level integration tests for the calculator (jsdom). Exercises the REAL store.js, engine.js,
 * ui.js and the REAL keypad markup from templates/components/calculator_modal.html.
 * MathLive's <math-field> is replaced by a minimal stub (jsdom cannot run MathLive);
 * the stub implements only the API surface ui.js uses.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const root = path.join(__dirname, '..');
const read = (p) => fs.readFileSync(path.join(root, p), 'utf8');
const STORE = read('static/js/store.js');
const ENGINE = read('static/js/calculator/engine.js');
const UI = read('static/js/calculator/ui.js');
const MODAL_HTML = read('templates/components/calculator_modal.html')
  .replace(/\{#[\s\S]*?#\}/g, '')
  .replace(/\{%[\s\S]*?%\}/g, '')
  .replace(/<script>[\s\S]*?<\/script>/g, '')
  .replace(/<link[^>]*>/g, '');

// Same vendored bundles the page serves (loaded inside the jsdom realm, like a browser)
const MATHJS = read('static/vendor/mathjs/math.min.js');
const NERDAMER = read('static/vendor/nerdamer/nerdamer.bundle.js');

let failures = 0;
function test(name, fn) {
  try { fn(); console.log(`✓ PASS: ${name}`); }
  catch (err) { failures += 1; console.error(`✗ FAIL: ${name}\n`, err); }
}

/** Build a page. opts.calculator=false simulates dashboard/landing (no modal rendered). */
function makePage({ calculator = true, savedMemento = null } = {}) {
  const dom = new JSDOM(`<!doctype html><html><body>
    <form id="answer-form"><label class="cbt-option-item"><span>A</span><input type="radio" name="option_id" value="1" checked></label></form>
    <div id="timer">12:34</div>
    ${calculator ? MODAL_HTML.replace('<div id="calc-mathfield-container"', '<div id="calc-mathfield-container"') : ''}
  </body></html>`, { url: 'https://kalmiprep.test/practice/session/1/', runScripts: 'outside-only', pretendToBeVisual: true });
  const { window } = dom;
  if (savedMemento) window.localStorage.setItem('kalmiprep_calc_memento', JSON.stringify(savedMemento));
  window.eval(MATHJS);
  window.eval(NERDAMER);

  // Minimal <math-field> stub: latex string value + the commands ui.js calls
  window.eval(`
    class StubMathField extends HTMLElement {
      constructor() { super(); this._v = ''; this.focusCount = 0; }
      get value() { return this._v; }
      set value(v) { this._v = v; }
      setValue(v) { this._v = v; }
      focus() { this.focusCount += 1; }
      executeCommand(cmd) {
        const [name, arg] = Array.isArray(cmd) ? cmd : [cmd];
        if (name === 'insert') this._v += String(arg).replace(/#\\?/g, '');
        else if (name === 'deleteBackward') this._v = this._v.slice(0, -1);
      }
    }
    customElements.define('math-field', StubMathField);
  `);
  return window;
}

function loadScripts(window, { store = true, calc = true } = {}) {
  if (store) window.eval(STORE);
  if (calc) {
    window.eval(ENGINE);
    window.eval(UI);
    window.KalmiCalcUI.init(); // jsdom's DOMContentLoaded fires asynchronously; page scripts run it after load
  }
}

const press = (window, action, payload) => window.KalmiCalcUI.handleKeyPress(action, payload);
const field = (window) => window.document.getElementById('calc-mathfield-container').querySelector('math-field');
const out = (window) => window.document.getElementById('calc-result-output').textContent;
const altC = (window) => window.document.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'c', altKey: true, bubbles: true, cancelable: true }));

console.log('--- RUNNING CALCULATOR INTEGRATION (JSDOM) TESTS ---');

// ---------- visibility / lifecycle ----------
test('Page WITHOUT the calculator modal: toggle, open and Alt+C are inert', () => {
  const w = makePage({ calculator: false });
  loadScripts(w, { calc: false });
  assert.strictEqual(w.document.getElementById('scientific-calculator-modal'), null);
  altC(w);
  w.useKalmiStore.getState().toggleCalc();
  w.useKalmiStore.getState().openCalc();
  assert.strictEqual(w.useKalmiStore.getState().calc.isOpen, false);
});

test('Calculator starts closed even if a stale memento says it was open', () => {
  const w = makePage({ savedMemento: { isOpen: true, expression: '9' } });
  loadScripts(w);
  assert.strictEqual(w.useKalmiStore.getState().calc.isOpen, false);
  assert.ok(w.document.getElementById('scientific-calculator-modal').classList.contains('hidden'));
});

test('Alt+C opens then closes the calculator; Escape closes it', () => {
  const w = makePage();
  loadScripts(w);
  altC(w);
  assert.strictEqual(w.useKalmiStore.getState().calc.isOpen, true);
  assert.ok(!w.document.getElementById('scientific-calculator-modal').classList.contains('hidden'));
  altC(w);
  assert.strictEqual(w.useKalmiStore.getState().calc.isOpen, false);
  altC(w);
  w.document.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  assert.strictEqual(w.useKalmiStore.getState().calc.isOpen, false);
});

test('Calc button path (toggleCalc) opens and closes', () => {
  const w = makePage();
  loadScripts(w);
  w.useKalmiStore.getState().toggleCalc();
  assert.strictEqual(w.useKalmiStore.getState().calc.isOpen, true);
  w.useKalmiStore.getState().toggleCalc();
  assert.strictEqual(w.useKalmiStore.getState().calc.isOpen, false);
});

test('Plain "c" key no longer opens the calculator', () => {
  const w = makePage();
  loadScripts(w);
  w.document.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'c', bubbles: true }));
  assert.strictEqual(w.useKalmiStore.getState().calc.isOpen, false);
});

test('Repeated initialisation (hx-boost re-execution) registers no duplicate listeners', () => {
  const w = makePage();
  loadScripts(w);
  loadScripts(w); // simulate body swap re-running the scripts
  loadScripts(w);
  w.KalmiCalcUI.init();
  w.KalmiCalcUI.init();
  altC(w);
  assert.strictEqual(w.useKalmiStore.getState().calc.isOpen, true, 'a single Alt+C must toggle exactly once');

  let closeCalls = 0;
  w.useKalmiStore.setState({ closeCalc: () => { closeCalls += 1; } });
  const keyBtn = w.document.querySelector('#scientific-calculator-modal button[onclick*="DIGIT"]');
  keyBtn.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }));
  assert.strictEqual(closeCalls, 1, 'Escape inside the modal must be handled exactly once');
});

// ---------- isolation from the exam ----------
test('Opening/closing leaves timer text, selected answer and form untouched; nothing is submitted', () => {
  const w = makePage();
  loadScripts(w);
  let submits = 0; let changes = 0;
  w.document.getElementById('answer-form').addEventListener('submit', () => { submits += 1; });
  w.document.querySelector('input[type=radio]').addEventListener('change', () => { changes += 1; });
  w.useKalmiStore.getState().openCalc();
  ['DIGIT:7', 'ADD', 'DIGIT:5', 'EQUALS', 'AC', 'DEL'].forEach((k) => { const [a, p] = k.split(':'); press(w, a, p); });
  w.useKalmiStore.getState().closeCalc();
  assert.strictEqual(submits, 0);
  assert.strictEqual(changes, 0);
  assert.strictEqual(w.document.querySelector('input[type=radio]').checked, true);
  assert.strictEqual(w.document.getElementById('timer').textContent, '12:34');
  assert.strictEqual(w.useKalmiStore.getState().timer.isRunning, false); // opening never starts/stops the exam timer
});

test('Keystrokes inside the calculator do not bubble to page-level (exam) shortcuts', () => {
  const w = makePage();
  loadScripts(w);
  w.useKalmiStore.getState().openCalc();
  let leaked = 0;
  w.document.addEventListener('keydown', () => { leaked += 1; });
  const f = field(w);
  ['1', 'a', 'C', 'Enter'].forEach((key) => f.dispatchEvent(new w.KeyboardEvent('keydown', { key, bubbles: true, cancelable: true })));
  const btn = w.document.querySelector('#scientific-calculator-modal button[onclick*="DIGIT"]');
  btn.dispatchEvent(new w.KeyboardEvent('keydown', { key: '2', bubbles: true }));
  assert.strictEqual(leaked, 0);
});

test('Every keypad button is type="button" (cannot submit a form)', () => {
  const buttons = MODAL_HTML.match(/<button\b[^>]*>/g) || [];
  assert.ok(buttons.length > 40);
  buttons.forEach((b) => assert.ok(/type="button"/.test(b), `button without type=button: ${b}`));
});

// ---------- keypad wiring (no dead / placeholder keys) ----------
test('Every onclick action on the keypad has a real handler', () => {
  const w = makePage();
  loadScripts(w);
  const used = new Set();
  const re = /KalmiCalcUI\.handleKeyPress\('([A-Z_]+)'/g;
  let m; while ((m = re.exec(MODAL_HTML))) used.add(m[1]);
  assert.ok(used.size > 30);
  used.forEach((a) => assert.ok(w.KalmiCalcUI.actions.includes(a), `no handler for keypad action ${a}`));
});

test('Mode menu advertises only implemented modes', () => {
  const modes = (MODAL_HTML.match(/selectMode\('([A-Z]+)'\)/g) || []).map((s) => s.match(/'([A-Z]+)'/)[1]);
  assert.deepStrictEqual(modes.sort(), ['CMPLX', 'COMP', 'EQN', 'STAT']);
  assert.ok(!/MATRIX|VECTOR|'MAT'|'VCT'/.test(MODAL_HTML));
});

// ---------- behaviour through the keypad ----------
test('Keypad: 2 + 3 = evaluates to 5; keyboard-entered 2+3 gives the same result', () => {
  const w = makePage();
  loadScripts(w);
  w.useKalmiStore.getState().openCalc();
  ['DIGIT:2', 'ADD', 'DIGIT:3', 'EQUALS'].forEach((k) => { const [a, p] = k.split(':'); press(w, a, p); });
  assert.strictEqual(field(w).value, '2+3');
  assert.strictEqual(out(w), '5');
  press(w, 'AC');
  field(w).value = '2+3'; // what MathLive holds after typing 2+3 on a physical keyboard
  field(w).dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }));
  assert.strictEqual(out(w), '5');
});

test('Natural structures are inserted as LaTeX (fraction, root, power, nth root)', () => {
  const w = makePage();
  loadScripts(w);
  press(w, 'FRAC'); assert.strictEqual(field(w).value, '\\frac{}{}');
  press(w, 'AC'); press(w, 'SQRT'); assert.strictEqual(field(w).value, '\\sqrt{}');
  press(w, 'AC'); press(w, 'POWER'); assert.strictEqual(field(w).value, '^{}');
  press(w, 'AC'); press(w, 'SHIFT'); press(w, 'SQRT'); assert.strictEqual(field(w).value, '\\sqrt[3]{}');
  press(w, 'AC'); press(w, 'SHIFT'); press(w, 'POWER'); assert.strictEqual(field(w).value, '\\sqrt[]{}');
});

test('SHIFT / ALPHA / HYP change the meaning of keys and auto-reset', () => {
  const w = makePage();
  loadScripts(w);
  press(w, 'SHIFT'); press(w, 'SIN'); assert.strictEqual(field(w).value, '\\arcsin\\left(\\right)');
  press(w, 'SIN'); assert.ok(field(w).value.endsWith('\\sin\\left(\\right)'), 'SHIFT must reset after one key');
  press(w, 'AC');
  press(w, 'HYP'); press(w, 'COS'); assert.strictEqual(field(w).value, '\\cosh\\left(\\right)');
  press(w, 'AC');
  press(w, 'ALPHA'); press(w, 'SIN'); assert.strictEqual(field(w).value, 'D');
});

test('DEG/RAD toggle changes trigonometric results (sin 30)', () => {
  const w = makePage();
  loadScripts(w);
  field(w).value = '\\sin\\left(30\\right)';
  press(w, 'EQUALS');
  assert.strictEqual(out(w), '0.5');
  press(w, 'ANGLE_TOGGLE'); // -> RAD, re-evaluates
  assert.strictEqual(w.KalmiCalcUI.getEngine().angleMode, 'RAD');
  assert.strictEqual(out(w), '-0.988031624093');
});

test('Errors are shown (not misleading results): 1/0 and 5+', () => {
  const w = makePage();
  loadScripts(w);
  field(w).value = '1\\div0'; press(w, 'EQUALS');
  assert.match(out(w), /Math ERROR/);
  field(w).value = '5+'; press(w, 'EQUALS');
  assert.match(out(w), /Syntax ERROR/);
});

test('Ans recall: result is reusable via the Ans key', () => {
  const w = makePage();
  loadScripts(w);
  field(w).value = '4\\times5'; press(w, 'EQUALS');
  press(w, 'AC'); press(w, 'ANS'); press(w, 'ADD'); press(w, 'DIGIT', '5');
  assert.strictEqual(field(w).value, '\\mathrm{Ans}+5');
  press(w, 'EQUALS');
  assert.strictEqual(out(w), '25');
});

test('Memory: M+ stores result, RCL inserts M, SHIFT+M+ subtracts, MC clears', () => {
  const w = makePage();
  loadScripts(w);
  const eng = w.KalmiCalcUI.getEngine();
  field(w).value = '6\\times7'; press(w, 'EQUALS');
  press(w, 'MEM_PLUS'); assert.strictEqual(eng.memory, 42);
  press(w, 'AC'); press(w, 'RCL'); press(w, 'ADD'); press(w, 'DIGIT', '8'); press(w, 'EQUALS');
  assert.strictEqual(out(w), '50');
  field(w).value = '2'; press(w, 'EQUALS');
  press(w, 'SHIFT'); press(w, 'MEM_PLUS'); assert.strictEqual(eng.memory, 40);
  press(w, 'MEM_CLEAR'); assert.strictEqual(eng.memory, 0);
});

test('STO: SHIFT+RCL then ALPHA variable key stores the answer; variable usable afterwards', () => {
  const w = makePage();
  loadScripts(w);
  field(w).value = '2+3'; press(w, 'EQUALS');
  press(w, 'SHIFT'); press(w, 'RCL'); // arms STO + ALPHA
  press(w, 'SIN'); // ALPHA+sin = D
  assert.strictEqual(w.KalmiCalcUI.getEngine().variables.D, 5);
  field(w).value = 'D\\times3'; press(w, 'EQUALS');
  assert.strictEqual(out(w), '15');
});

test('DEL removes one item; AC clears everything (different, predictable behaviour)', () => {
  const w = makePage();
  loadScripts(w);
  press(w, 'DIGIT', '1'); press(w, 'DIGIT', '2'); press(w, 'DIGIT', '3');
  press(w, 'DEL'); assert.strictEqual(field(w).value, '12');
  press(w, 'AC'); assert.strictEqual(field(w).value, ''); assert.strictEqual(out(w), '0');
});

test('History replay (REPLAY ▲▼) restores previous expressions', () => {
  const w = makePage();
  loadScripts(w);
  field(w).value = '1+1'; press(w, 'EQUALS');
  field(w).value = '2+2'; press(w, 'EQUALS');
  press(w, 'NAV_UP'); assert.strictEqual(field(w).value, '2+2');
  press(w, 'NAV_UP'); assert.strictEqual(field(w).value, '1+1');
  press(w, 'NAV_DOWN'); assert.strictEqual(field(w).value, '2+2');
});

test('Exact result: S⇔D toggles fraction / decimal display', () => {
  const w = makePage();
  loadScripts(w);
  field(w).value = '\\frac{1}{2}+\\frac{1}{3}'; press(w, 'EQUALS');
  assert.strictEqual(w.KalmiCalcUI._state.result.exactLatex, '\\frac{5}{6}');
  press(w, 'SD_TOGGLE');
  assert.strictEqual(out(w), '0.833333333333');
  press(w, 'SD_TOGGLE');
  assert.strictEqual(w.KalmiCalcUI._state.format, 'exact');
});

test('Mode changes: EQN solves, helper keys appear only in EQN/STAT', () => {
  const w = makePage();
  loadScripts(w);
  const helper = w.document.getElementById('calc-eqn-keys');
  assert.ok(helper.classList.contains('hidden'));
  w.KalmiCalcUI.selectMode('EQN');
  assert.ok(!helper.classList.contains('hidden'));
  field(w).value = 'x^2-5x+6=0'; press(w, 'EQUALS');
  assert.strictEqual(w.KalmiCalcUI._state.result.resultType, 'equation_roots');
  assert.deepStrictEqual(Array.from(w.KalmiCalcUI._state.result.roots), ['3', '2']);
  w.KalmiCalcUI.selectMode('COMP');
  assert.ok(helper.classList.contains('hidden'));
});

test('State persists (angle, memory, history) and the modal still starts closed on the next page', () => {
  const w1 = makePage();
  loadScripts(w1);
  const eng = w1.KalmiCalcUI.getEngine();
  press(w1, 'ANGLE_TOGGLE');
  field(w1).value = '9'; press(w1, 'EQUALS'); press(w1, 'MEM_PLUS');
  const saved = JSON.parse(w1.localStorage.getItem('kalmiprep_calc_memento'));
  assert.strictEqual(saved.angleMode, 'RAD');
  assert.strictEqual(saved.memory, 9);
  assert.ok(!('isOpen' in saved));

  const w2 = makePage({ savedMemento: saved });
  loadScripts(w2);
  assert.strictEqual(w2.KalmiCalcUI.getEngine().angleMode, 'RAD');
  assert.strictEqual(w2.KalmiCalcUI.getEngine().memory, 9);
  assert.strictEqual(w2.useKalmiStore.getState().calc.isOpen, false);
  assert.ok(eng);
});

test('Error text is rendered as text, never HTML', () => {
  const w = makePage();
  loadScripts(w);
  field(w).value = '<img src=x onerror=alert(1)>'; press(w, 'EQUALS');
  assert.strictEqual(w.document.querySelector('#calc-result-output img'), null);
});

console.log(failures === 0 ? '--- ALL CALCULATOR INTEGRATION TESTS PASSED ---' : `--- ${failures} TEST(S) FAILED ---`);
process.exit(failures === 0 ? 0 : 1);
