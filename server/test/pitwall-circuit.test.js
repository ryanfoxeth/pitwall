import test from 'node:test';
import assert from 'node:assert/strict';
import { circuitBounds } from '../services/pitwall/circuit.js';
test('circuit bounds reject missing and degenerate coordinates and preserve provider frame',()=>{
 assert.equal(circuitBounds([]),null);
 assert.equal(circuitBounds(Array.from({length:12},()=>({x:0,y:5}))),null);
 const points=Array.from({length:12},(_,i)=>({x:i-6,y:i*2}));
 assert.deepEqual(circuitBounds([...points,{x:NaN,y:1}]),{minX:-6,maxX:5,minY:0,maxY:22});
});
