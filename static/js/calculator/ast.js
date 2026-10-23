/**
 * KalmiPrep Scientific Calculator - Casio Mathematical AST & Template Engine
 * 
 * Provides true 2D Natural-V.P.A.M. mathematical structure:
 * - Nested stacked fractions: \frac{\Box}{\Box}
 * - Arbitrary base logarithms: \log_{\Box}(\Box)
 * - General nth roots: \sqrt[\Box]{\Box}
 * - Powers & exponents: \Box^{\Box}
 * - Absolute value: |\Box|
 * - 2D REPLAY Navigation (Up, Down, Left, Right across slots)
 * - Authentic Casio placeholder boxes (\Box) for unfilled slots
 * - Seamless compilation to KaTeX LaTeX and Math.js/Nerdamer expressions
 */

(function (global) {
  'use strict';

  let nextId = 1;
  function genId(prefix = 'slot') {
    return `${prefix}_${Date.now().toString(36)}_${nextId++}`;
  }

  class KalmiCalcAST {
    constructor() {
      this.clear();
    }

    clear() {
      this.slots = {}; // id -> { id, parentNodeId, slotName, items: [] }
      this.nodes = {}; // id -> { id, type, parentSlotId, slots: { name: slotId } }
      
      const rootId = 'root';
      this.slots[rootId] = {
        id: rootId,
        parentNodeId: null,
        slotName: 'root',
        items: []
      };

      this.cursor = {
        slotId: rootId,
        offset: 0
      };
    }

    // Clone/Serialize to JSON for Memento
    serialize() {
      return JSON.stringify({
        slots: this.slots,
        nodes: this.nodes,
        cursor: this.cursor
      });
    }

    // Deserialize from JSON
    deserialize(jsonStr) {
      if (!jsonStr) {
        this.clear();
        return;
      }
      try {
        const data = typeof jsonStr === 'string' ? JSON.parse(jsonStr) : jsonStr;
        if (data && data.slots && data.cursor) {
          this.slots = data.slots;
          this.nodes = data.nodes || {};
          this.cursor = data.cursor;
          return;
        }
      } catch (e) {}
      this.clear();
    }

    getActiveSlot() {
      if (!this.slots[this.cursor.slotId]) {
        this.cursor.slotId = 'root';
        this.cursor.offset = (this.slots.root && this.slots.root.items.length) || 0;
      }
      return this.slots[this.cursor.slotId];
    }

    // -----------------------------------------------------------------
    // Text & Operator Insertion
    // -----------------------------------------------------------------
    insertText(text) {
      if (!text) return;
      const slot = this.getActiveSlot();
      const chars = Array.from(text);

      for (const ch of chars) {
        slot.items.splice(this.cursor.offset, 0, ch);
        this.cursor.offset++;
      }
    }

    // -----------------------------------------------------------------
    // Template Insertion (Fractions, LogBase, NthRoot, Sqrt, Power, Abs)
    // -----------------------------------------------------------------
    insertTemplate(type, options = {}) {
      const slot = this.getActiveSlot();
      const nodeId = genId('node');
      let targetSlotId = null;

      if (type === 'fraction') {
        const numId = genId('num');
        const denId = genId('den');

        this.slots[numId] = { id: numId, parentNodeId: nodeId, slotName: 'num', items: [] };
        this.slots[denId] = { id: denId, parentNodeId: nodeId, slotName: 'den', items: [] };

        this.nodes[nodeId] = {
          id: nodeId,
          type: 'fraction',
          parentSlotId: slot.id,
          slots: { num: numId, den: denId }
        };

        slot.items.splice(this.cursor.offset, 0, { nodeId, type: 'fraction' });
        targetSlotId = numId;
      } 
      else if (type === 'logbase') {
        const baseId = genId('base');
        const argId = genId('arg');

        this.slots[baseId] = { id: baseId, parentNodeId: nodeId, slotName: 'base', items: [] };
        this.slots[argId] = { id: argId, parentNodeId: nodeId, slotName: 'arg', items: [] };

        this.nodes[nodeId] = {
          id: nodeId,
          type: 'logbase',
          parentSlotId: slot.id,
          slots: { base: baseId, arg: argId }
        };

        slot.items.splice(this.cursor.offset, 0, { nodeId, type: 'logbase' });
        targetSlotId = baseId;
      }
      else if (type === 'nthroot') {
        const indexId = genId('idx');
        const radId = genId('rad');

        this.slots[indexId] = { id: indexId, parentNodeId: nodeId, slotName: 'index', items: [] };
        this.slots[radId] = { id: radId, parentNodeId: nodeId, slotName: 'radicand', items: [] };

        this.nodes[nodeId] = {
          id: nodeId,
          type: 'nthroot',
          parentSlotId: slot.id,
          slots: { index: indexId, radicand: radId }
        };

        slot.items.splice(this.cursor.offset, 0, { nodeId, type: 'nthroot' });
        targetSlotId = indexId;
      }
      else if (type === 'sqrt') {
        const radId = genId('rad');

        this.slots[radId] = { id: radId, parentNodeId: nodeId, slotName: 'radicand', items: [] };

        this.nodes[nodeId] = {
          id: nodeId,
          type: 'sqrt',
          parentSlotId: slot.id,
          slots: { radicand: radId }
        };

        slot.items.splice(this.cursor.offset, 0, { nodeId, type: 'sqrt' });
        targetSlotId = radId;
      }
      else if (type === 'power') {
        const expId = genId('exp');

        this.slots[expId] = { id: expId, parentNodeId: nodeId, slotName: 'exp', items: [] };

        this.nodes[nodeId] = {
          id: nodeId,
          type: 'power',
          parentSlotId: slot.id,
          slots: { exp: expId }
        };

        slot.items.splice(this.cursor.offset, 0, { nodeId, type: 'power' });
        targetSlotId = expId;
      }
      else if (type === 'abs') {
        const bodyId = genId('abs');

        this.slots[bodyId] = { id: bodyId, parentNodeId: nodeId, slotName: 'body', items: [] };

        this.nodes[nodeId] = {
          id: nodeId,
          type: 'abs',
          parentSlotId: slot.id,
          slots: { body: bodyId }
        };

        slot.items.splice(this.cursor.offset, 0, { nodeId, type: 'abs' });
        targetSlotId = bodyId;
      }

      if (targetSlotId) {
        this.cursor.slotId = targetSlotId;
        this.cursor.offset = 0;
      }
    }

    // -----------------------------------------------------------------
    // Deletion (DEL / Backspace)
    // -----------------------------------------------------------------
    deleteBackward() {
      const slot = this.getActiveSlot();

      // Case 1: Cursor has items to its left in current slot
      if (this.cursor.offset > 0) {
        const prevItem = slot.items[this.cursor.offset - 1];

        // If previous item is a template node, delete the entire node and its slots
        if (prevItem && typeof prevItem === 'object' && prevItem.nodeId) {
          this.removeNode(prevItem.nodeId);
          slot.items.splice(this.cursor.offset - 1, 1);
          this.cursor.offset--;
          return;
        }

        // Previous item is a character
        slot.items.splice(this.cursor.offset - 1, 1);
        this.cursor.offset--;
        return;
      }

      // Case 2: Cursor is at start of a nested slot
      if (slot.parentNodeId) {
        const parentNode = this.nodes[slot.parentNodeId];
        if (!parentNode) return;

        // If the current slot is empty, remove the whole template and jump back to parent slot
        if (slot.items.length === 0) {
          const parentSlot = this.slots[parentNode.parentSlotId];
          if (parentSlot) {
            const idx = parentSlot.items.findIndex(item => item && item.nodeId === parentNode.id);
            if (idx !== -1) {
              parentSlot.items.splice(idx, 1);
              this.removeNode(parentNode.id);
              this.cursor.slotId = parentSlot.id;
              this.cursor.offset = idx;
              return;
            }
          }
        }

        // If not empty, step cursor out to left of template
        this.navLeft();
      }
    }

    removeNode(nodeId) {
      const node = this.nodes[nodeId];
      if (!node) return;
      if (node.slots) {
        for (const slotKey in node.slots) {
          const sId = node.slots[slotKey];
          if (this.slots[sId]) {
            // Recursively remove any child nodes
            for (const item of this.slots[sId].items) {
              if (item && item.nodeId) this.removeNode(item.nodeId);
            }
            delete this.slots[sId];
          }
        }
      }
      delete this.nodes[nodeId];
    }

    // -----------------------------------------------------------------
    // True 2D Casio REPLAY Navigation (Left, Right, Up, Down)
    // -----------------------------------------------------------------
    navLeft() {
      const slot = this.getActiveSlot();

      // 1. Move left within the current slot
      if (this.cursor.offset > 0) {
        const prev = slot.items[this.cursor.offset - 1];
        // If stepping into a template from the right, enter its last slot at the end
        if (prev && typeof prev === 'object' && prev.nodeId) {
          const node = this.nodes[prev.nodeId];
          if (node) {
            const lastSlotId = this.getNodeLastSlot(node);
            if (lastSlotId && this.slots[lastSlotId]) {
              this.cursor.slotId = lastSlotId;
              this.cursor.offset = this.slots[lastSlotId].items.length;
              return;
            }
          }
        }
        this.cursor.offset--;
        return;
      }

      // 2. We are at offset 0 of this slot. Check if we can step to a preceding slot in the same node
      if (slot.parentNodeId) {
        const node = this.nodes[slot.parentNodeId];
        if (node) {
          // Fraction: from den -> num
          if (node.type === 'fraction' && slot.slotName === 'den') {
            this.cursor.slotId = node.slots.num;
            this.cursor.offset = this.slots[node.slots.num].items.length;
            return;
          }
          // LogBase: from arg -> base
          if (node.type === 'logbase' && slot.slotName === 'arg') {
            this.cursor.slotId = node.slots.base;
            this.cursor.offset = this.slots[node.slots.base].items.length;
            return;
          }
          // NthRoot: from radicand -> index
          if (node.type === 'nthroot' && slot.slotName === 'radicand') {
            this.cursor.slotId = node.slots.index;
            this.cursor.offset = this.slots[node.slots.index].items.length;
            return;
          }

          // Otherwise, step out to parent slot before this node
          const parentSlot = this.slots[node.parentSlotId];
          if (parentSlot) {
            const idx = parentSlot.items.findIndex(it => it && it.nodeId === node.id);
            if (idx !== -1) {
              this.cursor.slotId = parentSlot.id;
              this.cursor.offset = idx;
              return;
            }
          }
        }
      }
    }

    navRight() {
      const slot = this.getActiveSlot();

      // 1. Move right within the current slot
      if (this.cursor.offset < slot.items.length) {
        const next = slot.items[this.cursor.offset];
        // If stepping into a template from the left, enter its first slot at the start
        if (next && typeof next === 'object' && next.nodeId) {
          const node = this.nodes[next.nodeId];
          if (node) {
            const firstSlotId = this.getNodeFirstSlot(node);
            if (firstSlotId && this.slots[firstSlotId]) {
              this.cursor.slotId = firstSlotId;
              this.cursor.offset = 0;
              return;
            }
          }
        }
        this.cursor.offset++;
        return;
      }

      // 2. We are at the end of this slot. Check if we can step to next slot in the same node
      if (slot.parentNodeId) {
        const node = this.nodes[slot.parentNodeId];
        if (node) {
          // Fraction: from num -> den
          if (node.type === 'fraction' && slot.slotName === 'num') {
            this.cursor.slotId = node.slots.den;
            this.cursor.offset = 0;
            return;
          }
          // LogBase: from base -> arg
          if (node.type === 'logbase' && slot.slotName === 'base') {
            this.cursor.slotId = node.slots.arg;
            this.cursor.offset = 0;
            return;
          }
          // NthRoot: from index -> radicand
          if (node.type === 'nthroot' && slot.slotName === 'index') {
            this.cursor.slotId = node.slots.radicand;
            this.cursor.offset = 0;
            return;
          }

          // Otherwise, exit to parent slot immediately after this node
          const parentSlot = this.slots[node.parentSlotId];
          if (parentSlot) {
            const idx = parentSlot.items.findIndex(it => it && it.nodeId === node.id);
            if (idx !== -1) {
              this.cursor.slotId = parentSlot.id;
              this.cursor.offset = idx + 1;
              return;
            }
          }
        }
      }
    }

    navUp() {
      const slot = this.getActiveSlot();

      // In Fraction: Denominator -> Numerator
      if (slot.parentNodeId) {
        const node = this.nodes[slot.parentNodeId];
        if (node && node.type === 'fraction' && slot.slotName === 'den') {
          this.cursor.slotId = node.slots.num;
          this.cursor.offset = Math.min(this.cursor.offset, this.slots[node.slots.num].items.length);
          return true;
        }
      }

      // If preceding item is a PowerNode, jump up into its exponent
      if (this.cursor.offset > 0) {
        const prev = slot.items[this.cursor.offset - 1];
        if (prev && typeof prev === 'object' && prev.nodeId) {
          const node = this.nodes[prev.nodeId];
          if (node && node.type === 'power') {
            this.cursor.slotId = node.slots.exp;
            this.cursor.offset = this.slots[node.slots.exp].items.length;
            return true;
          }
        }
      }

      // Root level start jump
      this.cursor.offset = 0;
      return false; // indicates top-level handled
    }

    navDown() {
      const slot = this.getActiveSlot();

      // In Fraction: Numerator -> Denominator
      if (slot.parentNodeId) {
        const node = this.nodes[slot.parentNodeId];
        if (node && node.type === 'fraction' && slot.slotName === 'num') {
          this.cursor.slotId = node.slots.den;
          this.cursor.offset = Math.min(this.cursor.offset, this.slots[node.slots.den].items.length);
          return true;
        }
        // In Power exponent: drop down to parent baseline
        if (node && node.type === 'power' && slot.slotName === 'exp') {
          const parentSlot = this.slots[node.parentSlotId];
          if (parentSlot) {
            const idx = parentSlot.items.findIndex(it => it && it.nodeId === node.id);
            if (idx !== -1) {
              this.cursor.slotId = parentSlot.id;
              this.cursor.offset = idx + 1;
              return true;
            }
          }
        }
      }

      // Root level end jump
      this.cursor.offset = slot.items.length;
      return false;
    }

    getNodeFirstSlot(node) {
      if (!node || !node.slots) return null;
      if (node.type === 'fraction') return node.slots.num;
      if (node.type === 'logbase') return node.slots.base;
      if (node.type === 'nthroot') return node.slots.index;
      if (node.type === 'sqrt') return node.slots.radicand;
      if (node.type === 'power') return node.slots.exp;
      if (node.type === 'abs') return node.slots.body;
      return Object.values(node.slots)[0] || null;
    }

    getNodeLastSlot(node) {
      if (!node || !node.slots) return null;
      if (node.type === 'fraction') return node.slots.den;
      if (node.type === 'logbase') return node.slots.arg;
      if (node.type === 'nthroot') return node.slots.radicand;
      if (node.type === 'sqrt') return node.slots.radicand;
      if (node.type === 'power') return node.slots.exp;
      if (node.type === 'abs') return node.slots.body;
      const vals = Object.values(node.slots);
      return vals[vals.length - 1] || null;
    }

    isEmpty() {
      const root = this.slots.root;
      return !root || root.items.length === 0;
    }

    // -----------------------------------------------------------------
    // LaTeX Generation with Authentic Casio Placeholder Boxes & Cursor
    // -----------------------------------------------------------------
    toLatex(showCursor = true) {
      return this.renderSlotLatex('root', showCursor);
    }

    renderSlotLatex(slotId, showCursor) {
      const slot = this.slots[slotId];
      if (!slot) return '';

      const isActiveSlot = showCursor && this.cursor.slotId === slotId;
      const cursorMarkup = showCursor ? '__CALC_CURSOR__' : '';

      // Authentic Casio Placeholder Box (\Box)
      if (slot.items.length === 0) {
        if (isActiveSlot) {
          return `{\\Box} ${cursorMarkup}`;
        }
        return `{\\Box}`;
      }

      let res = '';
      for (let i = 0; i < slot.items.length; i++) {
        if (isActiveSlot && this.cursor.offset === i) {
          res += cursorMarkup;
        }

        const it = slot.items[i];
        if (typeof it === 'string') {
          res += this.escapeLatexToken(it);
        } else if (it && it.nodeId) {
          const node = this.nodes[it.nodeId];
          if (node) {
            res += this.renderNodeLatex(node, showCursor);
          }
        }
      }

      if (isActiveSlot && this.cursor.offset === slot.items.length) {
        res += cursorMarkup;
      }

      return res;
    }

    renderNodeLatex(node, showCursor) {
      if (node.type === 'fraction') {
        const numLatex = this.renderSlotLatex(node.slots.num, showCursor);
        const denLatex = this.renderSlotLatex(node.slots.den, showCursor);
        return `\\frac{${numLatex}}{${denLatex}}`;
      }
      if (node.type === 'logbase') {
        const baseLatex = this.renderSlotLatex(node.slots.base, showCursor);
        const argLatex = this.renderSlotLatex(node.slots.arg, showCursor);
        return `\\log_{${baseLatex}}\\left(${argLatex}\\right)`;
      }
      if (node.type === 'nthroot') {
        const idxLatex = this.renderSlotLatex(node.slots.index, showCursor);
        const radLatex = this.renderSlotLatex(node.slots.radicand, showCursor);
        return `\\sqrt[${idxLatex}]{${radLatex}}`;
      }
      if (node.type === 'sqrt') {
        const radLatex = this.renderSlotLatex(node.slots.radicand, showCursor);
        return `\\sqrt{${radLatex}}`;
      }
      if (node.type === 'power') {
        const expLatex = this.renderSlotLatex(node.slots.exp, showCursor);
        return `^{${expLatex}}`;
      }
      if (node.type === 'abs') {
        const bodyLatex = this.renderSlotLatex(node.slots.body, showCursor);
        return `\\left|${bodyLatex}\\right|`;
      }
      return '';
    }

    escapeLatexToken(token) {
      if (token === '×' || token === '*') return '\\times ';
      if (token === '÷' || token === '/') return '\\div ';
      if (token === '−' || token === '-') return '-';
      if (token === '+') return '+';
      if (token === 'π') return '\\pi ';
      if (token === 'sin(') return '\\sin(';
      if (token === 'cos(') return '\\cos(';
      if (token === 'tan(') return '\\tan(';
      if (token === 'asin(') return '\\sin^{-1}(';
      if (token === 'acos(') return '\\cos^{-1}(';
      if (token === 'atan(') return '\\tan^{-1}(';
      if (token === 'ln(') return '\\ln(';
      if (token === 'log(') return '\\log(';
      if (token === 'Ans') return '\\mathrm{Ans}';
      if (token === 'EXP') return '\\times 10^{';
      if (token === 'nPr') return '\\mathrm{P}';
      if (token === 'nCr') return '\\mathrm{C}';
      return token;
    }

    // -----------------------------------------------------------------
    // Math.js & Nerdamer Compilation
    // -----------------------------------------------------------------
    toMathString(lastAns = 0) {
      return this.compileSlotMath('root', lastAns);
    }

    compileSlotMath(slotId, lastAns) {
      const slot = this.slots[slotId];
      if (!slot) return '0';
      if (slot.items.length === 0) return '0';

      let out = '';
      for (const it of slot.items) {
        if (typeof it === 'string') {
          if (it === '×') out += '*';
          else if (it === '÷') out += '/';
          else if (it === '−') out += '-';
          else if (it === 'π') out += 'pi';
          else if (it === 'Ans') out += `(${parseFloat(lastAns) || 0})`;
          else if (it === 'EXP') out += '*10^';
          else out += it;
        } else if (it && it.nodeId) {
          const node = this.nodes[it.nodeId];
          if (node) {
            out += this.compileNodeMath(node, lastAns);
          }
        }
      }
      return out;
    }

    compileNodeMath(node, lastAns) {
      if (node.type === 'fraction') {
        const num = this.compileSlotMath(node.slots.num, lastAns) || '0';
        const den = this.compileSlotMath(node.slots.den, lastAns) || '1';
        return `((${num}) / (${den}))`;
      }
      if (node.type === 'logbase') {
        const base = this.compileSlotMath(node.slots.base, lastAns) || '10';
        const arg = this.compileSlotMath(node.slots.arg, lastAns) || '1';
        // log(arg, base) in Math.js
        return `(log(${arg}, ${base}))`;
      }
      if (node.type === 'nthroot') {
        const idx = this.compileSlotMath(node.slots.index, lastAns) || '2';
        const rad = this.compileSlotMath(node.slots.radicand, lastAns) || '0';
        return `(nthRoot(${rad}, ${idx}))`;
      }
      if (node.type === 'sqrt') {
        const rad = this.compileSlotMath(node.slots.radicand, lastAns) || '0';
        return `(sqrt(${rad}))`;
      }
      if (node.type === 'power') {
        const exp = this.compileSlotMath(node.slots.exp, lastAns) || '1';
        return `^(${exp})`;
      }
      if (node.type === 'abs') {
        const body = this.compileSlotMath(node.slots.body, lastAns) || '0';
        return `(abs(${body}))`;
      }
      return '';
    }
  }

  // Export
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = KalmiCalcAST;
  }
  if (typeof global !== 'undefined') {
    global.KalmiCalcAST = KalmiCalcAST;
  }
})(typeof window !== 'undefined' ? window : globalThis);
