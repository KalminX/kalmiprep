/**
 * Automated Mathematical Test Suite for KalmiCalcEngine
 * Runs in Node.js environment to verify mathematical correctness across all required domains.
 */

const assert = require('assert');
const math = require('mathjs');

global.math = math;

// Load KalmiCalcEngine
const { KalmiCalcEngine, factorial, balanceParentheses, cleanExpression } = require('../static/js/calculator/engine.js');

const engine = new KalmiCalcEngine(math);

let failures = 0;
function test(name, fn) {
  try {
    fn();
    console.log(`✓ PASS: ${name}`);
  } catch (err) {
    console.error(`✗ FAIL: ${name}`);
    console.error(err);
    failures += 1;
  }
}

console.log('--- RUNNING MATHEMATICAL ENGINE TESTS ---');

// 1. Basic Arithmetic & Precedence
test('Basic arithmetic precedence: 1 + 2 * 3 = 7', () => {
  const res = engine.evaluate('1 + 2 * 3');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.result, '7');
});

test('Parentheses override precedence: (1 + 2) * 3 = 9', () => {
  const res = engine.evaluate('(1 + 2) * 3');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.result, '9');
});

test('Decimal arithmetic: 0.1 + 0.2 precision handling', () => {
  const res = engine.evaluate('0.1 + 0.2');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.result, '0.3');
});

test('Division: 1 / 4 = 0.25', () => {
  const res = engine.evaluate('1 / 4');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.result, '0.25');
});

test('Division by zero produces Math ERROR', () => {
  const res = engine.evaluate('5 / 0');
  assert.strictEqual(res.success, false);
  assert.strictEqual(res.error, 'Math ERROR');
});

// 2. Powers and Exponents
test('Powers: 2^3 = 8', () => {
  const res = engine.evaluate('2^3');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.result, '8');
});

test('Negative exponents: 2^-1 = 0.5', () => {
  const res = engine.evaluate('2^(-1)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.result, '0.5');
});

test('Power of 10: 10^3 = 1000', () => {
  const res = engine.evaluate('10^3');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.result, '1000');
});

// 3. Roots
test('Square root: sqrt(16) = 4', () => {
  const res = engine.evaluate('sqrt(16)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.result, '4');
});

test('Cube root: cbrt(27) = 3', () => {
  const res = engine.evaluate('cbrt(27)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.result, '3');
});

// 4. Trigonometry (DEG & RAD)
test('Trig DEG: sin(30) = 0.5, cos(60) = 0.5, tan(45) = 1', () => {
  const sin30 = engine.evaluate('sin(30)', 'DEG');
  assert.strictEqual(sin30.success, true);
  assert.strictEqual(sin30.result, '0.5');

  const cos60 = engine.evaluate('cos(60)', 'DEG');
  assert.strictEqual(cos60.success, true);
  assert.strictEqual(cos60.result, '0.5');

  const tan45 = engine.evaluate('tan(45)', 'DEG');
  assert.strictEqual(tan45.success, true);
  assert.strictEqual(tan45.result, '1');
});

test('Trig DEG boundary snap: cos(90) = 0', () => {
  const cos90 = engine.evaluate('cos(90)', 'DEG');
  assert.strictEqual(cos90.success, true);
  assert.strictEqual(cos90.result, '0');
});

test('Trig DEG undefined asymptote: tan(90) = Math ERROR', () => {
  const tan90 = engine.evaluate('tan(90)', 'DEG');
  assert.strictEqual(tan90.success, false);
  assert.strictEqual(tan90.error, 'Math ERROR');
});

test('Trig RAD: sin(pi / 2) = 1, cos(pi) = -1', () => {
  const sinPi2 = engine.evaluate('sin(pi / 2)', 'RAD');
  assert.strictEqual(sinPi2.success, true);
  assert.strictEqual(sinPi2.result, '1');

  const cosPi = engine.evaluate('cos(pi)', 'RAD');
  assert.strictEqual(cosPi.success, true);
  assert.strictEqual(cosPi.result, '-1');
});

// 5. Inverse Trigonometry
test('Inverse Trig DEG: asin(0.5) = 30, acos(0.5) = 60, atan(1) = 45', () => {
  const asinRes = engine.evaluate('asin(0.5)', 'DEG');
  assert.strictEqual(asinRes.success, true);
  assert.strictEqual(asinRes.result, '30');

  const acosRes = engine.evaluate('acos(0.5)', 'DEG');
  assert.strictEqual(acosRes.success, true);
  assert.strictEqual(acosRes.result, '60');

  const atanRes = engine.evaluate('atan(1)', 'DEG');
  assert.strictEqual(atanRes.success, true);
  assert.strictEqual(atanRes.result, '45');
});

// 6. Logarithms & Exponentials
test('Common log: log(100) = 2', () => {
  const res = engine.evaluate('log(100)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.result, '2');
});

test('Natural log: ln(e) = 1', () => {
  const res = engine.evaluate('ln(e)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.result, '1');
});

// 7. Factorial
test('Factorials: 0! = 1, 5! = 120', () => {
  assert.strictEqual(factorial(0), 1);
  assert.strictEqual(factorial(1), 1);
  assert.strictEqual(factorial(5), 120);

  const res = engine.evaluate('factorial(5)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.result, '120');
});

// 8. Scientific Exponential & Percentage
test('EXP notation: 1.6 EXP 3 = 1600', () => {
  const res = engine.evaluate('1.6 EXP 3');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.result, '1600');
});

test('Percentage: 200 * 15% = 30', () => {
  const res = engine.evaluate('200 * 15%');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.result, '30');
});

// 9. Ans Memory
test('Ans chaining: Ans + 10 with Ans=5 gives 15', () => {
  const res = engine.evaluate('Ans + 10', 'DEG', 5);
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.result, '15');
});

// 10. Parentheses Auto-Balancing
test('Auto-balancing: sin(30 automatically balances to sin(30) = 0.5', () => {
  const res = engine.evaluate('sin(30', 'DEG');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.result, '0.5');
});

console.log(failures === 0 ? '--- ALL MATHEMATICAL ENGINE TESTS PASSED ---' : `--- ${failures} TEST(S) FAILED ---`);
process.exit(failures === 0 ? 0 : 1);
