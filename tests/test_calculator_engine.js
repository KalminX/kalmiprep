/**
 * Automated Mathematical Test Suite for KalmiCalcEngine
 * Runs in Node.js environment to verify all mathematical correctness requirements.
 */

const assert = require('assert');
const math = require('../node_modules/mathjs');
const nerdamer = require('../node_modules/nerdamer/dist/bundle.js');

global.math = math;
global.nerdamer = nerdamer;

// Load KalmiCalcEngine
require('../static/js/calculator/engine.js');

const engine = new global.KalmiCalcEngine();

function test(name, fn) {
  try {
    fn();
    console.log(`✓ PASS: ${name}`);
  } catch (err) {
    console.error(`✗ FAIL: ${name}`);
    console.error(err);
    process.exit(1);
  }
}

console.log('--- RUNNING MATHEMATICAL ENGINE TESTS ---');

// 1. Basic Arithmetic & Precedence
test('Basic arithmetic precedence: 1 + 2 * 3 = 7', () => {
  const res = engine.evaluate('1 + 2 \\times 3');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '7');
});

test('Parentheses override precedence: (1 + 2) * 3 = 9', () => {
  const res = engine.evaluate('\\left(1 + 2\\right) \\times 3');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '9');
});

test('Fractions: 1/2 + 1/3 = 5/6 (exact) and ~0.833333333333 (decimal)', () => {
  const res = engine.evaluate('\\frac{1}{2} + \\frac{1}{3}');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.exactLatex, '\\frac{5}{6}');
  assert.strictEqual(res.decimal, '0.833333333333');
  assert.strictEqual(res.isExact, true);
});

test('Nested fractions: 1 / (1 + 1/2) = 2/3', () => {
  const res = engine.evaluate('\\frac{1}{1 + \\frac{1}{2}}');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.exactLatex, '\\frac{2}{3}');
  assert.strictEqual(res.decimal, '0.666666666667');
});

// 2. Powers and Nested Exponents
test('Powers: 2^3 = 8', () => {
  const res = engine.evaluate('2^{3}');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '8');
});

test('Nested powers: 2^(3^2) = 512', () => {
  const res = engine.evaluate('2^{3^{2}}');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '512');
});

test('Negative base powers: (-2)^4 = 16', () => {
  const res = engine.evaluate('\\left(-2\\right)^{4}');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '16');
});

test('Unary minus with power: -2^4 = -16', () => {
  const res = engine.evaluate('-2^{4}');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '-16');
});

test('Negative exponents: 2^(-3) = 0.125 and exact 1/8', () => {
  const res = engine.evaluate('2^{-3}');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '0.125');
  assert.strictEqual(res.exactLatex, '\\frac{1}{8}');
});

// 3. Roots
test('Square roots: sqrt(16) = 4', () => {
  const res = engine.evaluate('\\sqrt{16}');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '4');
});

test('Square roots simplification: sqrt(18) = 3*sqrt(2) ~ 4.24264068712', () => {
  const res = engine.evaluate('\\sqrt{18}');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '4.24264068712');
  assert.strictEqual(res.isExact, true);
});

test('Cube root: sqrt[3]{27} = 3', () => {
  const res = engine.evaluate('\\sqrt[3]{27}');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '3');
});

test('4th root: sqrt[4]{16} = 2', () => {
  const res = engine.evaluate('\\sqrt[4]{16}');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '2');
});

// 4. Trigonometry in DEG and RAD Modes
test('DEG mode: sin(30) = 0.5', () => {
  engine.setAngleMode('DEG');
  const res = engine.evaluate('\\sin(30)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '0.5');
});

test('DEG mode: cos(60) = 0.5', () => {
  engine.setAngleMode('DEG');
  const res = engine.evaluate('\\cos(60)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '0.5');
});

test('DEG mode: cos(90) = 0 (exact zero)', () => {
  engine.setAngleMode('DEG');
  const res = engine.evaluate('\\cos(90)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '0');
});

test('DEG mode: tan(45) = 1', () => {
  engine.setAngleMode('DEG');
  const res = engine.evaluate('\\tan(45)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '1');
});

test('DEG mode: tan(90) = Math ERROR (singularity)', () => {
  engine.setAngleMode('DEG');
  const res = engine.evaluate('\\tan(90)');
  assert.strictEqual(res.success, false);
  assert.match(res.error, /Math ERROR/);
});

test('DEG mode: asin(0.5) = 30 deg', () => {
  engine.setAngleMode('DEG');
  const res = engine.evaluate('\\arcsin(0.5)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '30');
});

test('RAD mode: sin(pi/6) = 0.5', () => {
  engine.setAngleMode('RAD');
  const res = engine.evaluate('\\sin(\\frac{\\pi}{6})');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '0.5');
});

test('RAD mode: cos(pi/2) = 0', () => {
  engine.setAngleMode('RAD');
  const res = engine.evaluate('\\cos(\\frac{\\pi}{2})');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '0');
});

// 5. Logarithms
test('Logarithms: log(100) = 2', () => {
  const res = engine.evaluate('\\log(100)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '2');
});

test('Natural Logarithms: ln(e) = 1', () => {
  const res = engine.evaluate('\\ln(e)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '1');
});

test('Arbitrary base Logarithms: log_2(8) = 3', () => {
  const res = engine.evaluate('\\log_{2}{8}');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '3');
});

// 6. Factorials & Combinatorics
test('Factorial: 5! = 120', () => {
  const res = engine.evaluate('5!');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '120');
});

test('Permutations: 5 P 3 = 60', () => {
  const res = engine.evaluate('5 P 3');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '60');
});

test('Combinations: 5 C 3 = 10', () => {
  const res = engine.evaluate('5 C 3');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '10');
});

// 7. Complex Numbers & Exponents
test('Complex addition: (2+3i) + (4-i) = 6 + 2i', () => {
  const res = engine.evaluate('(2 + 3i) + (4 - i)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '6 + 2i');
  assert.strictEqual(res.resultType, 'complex');
});

test('Complex square: (1+i)^2 = 2i', () => {
  const res = engine.evaluate('(1 + i)^{2}');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '2i');
});

test('Complex division: 1/i = -i', () => {
  const res = engine.evaluate('\\frac{1}{i}');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '-i');
});

test('Complex exponent: 2^(3+4i) = -7.46149661469 + 2.88549272551i (principal value)', () => {
  const res = engine.evaluate('2^{3 + 4i}');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '-7.46149661469 + 2.88549272551i');
});

test('Complex modulus: |3 + 4i| = 5', () => {
  const res = engine.evaluate('|3 + 4i|');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '5');
});

// 8. Error Handling
test('Division by zero: 5 / 0 returns Math ERROR', () => {
  const res = engine.evaluate('5 / 0');
  assert.strictEqual(res.success, false);
  assert.match(res.error, /Math ERROR/);
});

test('Syntax error: 5 + returns Syntax ERROR', () => {
  const res = engine.evaluate('5 +');
  assert.strictEqual(res.success, false);
  assert.match(res.error, /Syntax ERROR/);
});

test('Domain error: sqrt(-4) in COMP mode is a Math ERROR (not silently complex)', () => {
  engine.setMode('COMP');
  const res = engine.evaluate('\\sqrt{-4}');
  assert.strictEqual(res.success, false);
  assert.match(res.error, /Math ERROR/);
});

test('Domain error: ln(-1) in COMP mode is a Math ERROR', () => {
  const res = engine.evaluate('\\ln(-1)');
  assert.strictEqual(res.success, false);
});

test('Domain error: asin(2) is a Math ERROR', () => {
  const res = engine.evaluate('\\arcsin(2)');
  assert.strictEqual(res.success, false);
});

test('Domain error: (-3)! is a Math ERROR', () => {
  const res = engine.evaluate('\\left(-3\\right)!');
  assert.strictEqual(res.success, false);
});

test('Implicit multiplication does not corrupt function names: 2log(100) = 4', () => {
  const res = engine.evaluate('2\\log(100)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '4');
});

test('Decimal times parenthesis: 2.5(2) = 5', () => {
  const res = engine.evaluate('2.5(2)');
  assert.strictEqual(res.decimal, '5');
});

test('Scientific notation: 1.6 x 10^-19 * 2 = 3.2e-19', () => {
  const res = engine.evaluate('1.6\\times10^{-19}\\times 2');
  assert.strictEqual(res.success, true);
  assert.strictEqual(Number(res.decimal), 3.2e-19);
});

// 9. Memory & Ans
test('Ans recall and calculation chaining', () => {
  const res1 = engine.evaluate('4 \\times 5');
  assert.strictEqual(res1.decimal, '20');
  const res2 = engine.evaluate('Ans + 5');
  assert.strictEqual(res2.decimal, '25');
});

test('Memory M+ and recall operations', () => {
  engine.memory = 0;
  engine.evaluate('15');
  engine.memory += 15;
  assert.strictEqual(engine.memory, 15);
  const res = engine.evaluate('M + 5');
  assert.strictEqual(res.decimal, '20');
});

// 10. Equation Solver (EQN Mode)
test('Equation solver quadratic: x^2 - 5x + 6 = 0 gives roots 3, 2', () => {
  const res = engine.solveEquation('x^2 - 5*x + 6 = 0');
  assert.strictEqual(res.success, true);
  assert.deepStrictEqual(res.roots, ['3', '2']);
  assert.strictEqual(res.resultType, 'equation_roots');
});

test('Equation solver linear: 2x + 4 = 10 gives root 3', () => {
  const res = engine.solveEquation('2*x + 4 = 10');
  assert.strictEqual(res.success, true);
  assert.deepStrictEqual(res.roots, ['3']);
});

test('Equation solver cubic: x^3 - 6x^2 + 11x - 6 = 0 gives roots 3, 2, 1', () => {
  const res = engine.solveEquation('x^3 - 6*x^2 + 11*x - 6 = 0');
  assert.strictEqual(res.success, true);
  assert.deepStrictEqual(res.roots, ['3', '2', '1']);
});

test('Equation solver complex: x^2 + 1 = 0 gives roots i, -i', () => {
  const res = engine.solveEquation('x^2 + 1 = 0');
  assert.strictEqual(res.success, true);
  assert.deepStrictEqual(res.roots, ['i', '-i']);
});

// 11. Statistics Mode
test('Statistics mode: stat(1, 2, 3, 4, 5)', () => {
  engine.setMode('STAT');
  const res = engine.evaluate('stat(1, 2, 3, 4, 5)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.statSummary.mean, 3);
  assert.strictEqual(res.statSummary.sum, 15);
  assert.strictEqual(res.statSummary.n, 5);
});

test('Statistics mode accepts MathLive-serialised parentheses (\\left( \\right))', () => {
  engine.setMode('STAT');
  const res = engine.evaluate('stat\\left(2,4,6\\right)');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.statSummary.mean, 4);
  engine.setMode('COMP');
});

// 12. MathLive serialisation forms (no spaces) and degree literals
test('MathLive-style permutation/combination without spaces: 5P3, 5C3', () => {
  assert.strictEqual(engine.evaluate('5P3').decimal, '60');
  assert.strictEqual(engine.evaluate('5C3').decimal, '10');
});

test('2\\pi is not misread as a permutation', () => {
  engine.setAngleMode('RAD');
  const res = engine.evaluate('2\\pi');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '6.28318530718');
});

test('Degree literal in DEG mode: sin(30^\\circ) = 0.5', () => {
  engine.setAngleMode('DEG');
  assert.strictEqual(engine.evaluate('\\sin\\left(30^\\circ\\right)').decimal, '0.5');
});

test('Degree literal in RAD mode converts to radians: sin(30^\\circ) = 0.5', () => {
  engine.setAngleMode('RAD');
  assert.strictEqual(engine.evaluate('\\sin\\left(30^{\\circ}\\right)').decimal, '0.5');
  engine.setAngleMode('DEG');
});

test('Hyperbolic functions: sinh(0) = 0, cosh(0) = 1', () => {
  assert.strictEqual(engine.evaluate('\\sinh\\left(0\\right)').decimal, '0');
  assert.strictEqual(engine.evaluate('\\cosh\\left(0\\right)').decimal, '1');
});

test('Absolute value of complex via MathLive |..|', () => {
  assert.strictEqual(engine.evaluate('\\left|3+4i\\right|').decimal, '5');
});

test('CMPLX mode allows sqrt(-4) = 2i (principal root)', () => {
  engine.setMode('CMPLX');
  const res = engine.evaluate('\\sqrt{-4}');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '2i');
  engine.setMode('COMP');
});

test('Unavailable modes are rejected (no fake MAT/VCT modes)', () => {
  engine.setMode('MAT');
  assert.strictEqual(engine.mode, 'COMP');
  engine.setMode('VCT');
  assert.strictEqual(engine.mode, 'COMP');
});

test('Ans recalls complex answers within the session', () => {
  engine.evaluate('2^{3+4i}');
  const res = engine.evaluate('Ans');
  assert.strictEqual(res.success, true);
  assert.strictEqual(res.decimal, '-7.46149661469 + 2.88549272551i');
});

test('Variables: stored value is usable in expressions', () => {
  engine.setVariable('A', 7);
  assert.strictEqual(engine.evaluate('A\\times 3').decimal, '21');
});

test('No eval()/Function() in calculator sources', () => {
  const fs = require('fs');
  const path = require('path');
  const dir = path.join(__dirname, '..', 'static', 'js');
  const files = ['store.js', 'calculator/engine.js', 'calculator/ui.js']
    .map((f) => fs.readFileSync(path.join(dir, f), 'utf8').replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, ''));
  files.forEach((src) => {
    assert.ok(!/\beval\s*\(/.test(src), 'eval( found');
    assert.ok(!/new\s+Function\s*\(/.test(src), 'new Function( found');
  });
});

console.log('--- ALL MATHEMATICAL ENGINE TESTS PASSED SUCCESSFULLY! ---');
