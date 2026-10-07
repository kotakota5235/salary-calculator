const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const context = {window: {}};
vm.createContext(context);
for (const file of ['holidays.js', 'calculator.js']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', file), 'utf8'), context);
const calc = (text, year = 2026) => context.SalaryCalculator.calculate(text, year, context.window.HOLIDAYS);
const valid = (text, amount, minutes) => {
  const r = calc(text); assert.equal(r.errors.length, 0, r.errors.join('\n'));
  assert.equal(r.units / 60, amount); assert.equal(r.minutes, minutes);
};
test('平日の3時間帯を分割', () => valid('10/05(月) 12:00～18:00 06:00 00:00', 7520, 360));
test('土曜・祝日・振替休日・国民の休日', () => {
  for (const date of ['10/10', '10/12']) valid(`${date} 13:00〜17:30`, 6052.5, 270);
  for (const date of ['05/06', '09/22']) valid(`${date} 13:00〜17:30`, 5805, 270);
});
test('17時と13時の境界', () => {
  valid('10/05 12:59～13:01', (1195 + 1245) / 60, 2);
  valid('10/05 16:59～17:01', (1245 + 1345) / 60, 2);
});
test('年またぎは年指定、曜日は日付から算出', () => {
  const r = calc('12/31(木) 17:00～20:00\n2027/01/01(金) 12:00～13:00');
  assert.equal(r.errors.length, 0); assert.equal(r.units / 60, 5380);
  assert.equal(r.shifts[1].key, '2027-01-01');
});
test('全角・ヘッダー・勤務なし', () => valid('日付\t勤務時間\t労働時間\t休憩時間\n１０/０５（月）　１７：００～２０：００　０３：００　００：００\n10/06(火) －\n10/07(水) ー', 4035, 180));
test('同日の分割勤務は1日と数える', () => {
  const r = calc('10/05 10:00～12:00\n10/05 13:00～17:00');
  assert.equal(r.errors.length, 0); assert.equal(r.days, 1); assert.equal(r.units / 60, 7370);
});
test('24時ちょうどを許容', () => valid('10/05 23:00～24:00', 1345, 60));
test('うるう日検証', () => { assert.equal(calc('02/29 10:00～11:00', 2024).errors.length, 0); assert.ok(calc('02/29 10:00～11:00').errors.length); });
for (const input of ['', '不明な行', '02/30 17:00～20:00', '10/05 17:60～20:00', '10/05 25:00～26:00', '10/05 20:00～17:00', '10/05 17:00～17:00', '10/05 12:00～18:00 05:00 01:00', '10/05 12:00～18:00 05:00 00:00', '10/05 17:00～20:00\n10/05 19:00～21:00', '2028/01/01 17:00～20:00']) {
  test(`不正入力を部分計算せず報告: ${input}`, () => {const r = calc(input); assert.ok(r.errors.length); assert.equal(r.units, undefined);});
}
test('年入力の検証', () => {for (const y of [0, 2028, 2026.5, NaN]) assert.ok(calc('10/05 17:00～20:00', y).errors.length);});

test('改定日の前後を勤務日で判定', () => {
  valid('09/30 12:00～18:00', 7190, 360);
  valid('10/01 12:00～18:00', 7520, 360);
  valid('09/30 12:00～18:00\n10/01 12:00～18:00', 14710, 720);
});
