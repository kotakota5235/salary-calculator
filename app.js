'use strict';
const el = id => document.getElementById(id);
const yen = units => `${Math.round(units / 60).toLocaleString('ja-JP')}円`;
const clock = minutes => `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`;
const yearInput = el('year');
yearInput.min = HOLIDAYS.minYear;
yearInput.max = HOLIDAYS.maxYear;
yearInput.value = new Date().getFullYear();
el('holiday-range').textContent = `${HOLIDAYS.minYear}〜${HOLIDAYS.maxYear}`;
const invalidate = () => { el('results').hidden = true; el('messages').hidden = true; };
el('shift-form').addEventListener('input', invalidate);
el('sample').addEventListener('click', () => {
  yearInput.value = 2026;
  el('shifts').value = '日付\t勤務時間\t労働時間\t休憩時間\n10/05(月)\t12:00～18:00\t06:00\t00:00\n10/10(土)\t17:00～20:00\t03:00\t00:00\n10/12(月)\t13:00～17:30\t04:30\t00:00';
  invalidate();
  el('shifts').focus();
});
function node(tag, content, className) {
  const result = document.createElement(tag);
  if (content !== undefined) result.textContent = content;
  if (className) result.className = className;
  return result;
}
el('shift-form').addEventListener('submit', event => {
  event.preventDefault();
  invalidate();
  const result = SalaryCalculator.calculate(el('shifts').value, Number(yearInput.value), HOLIDAYS);
  if (result.errors.length) {
    el('messages').textContent = '入力内容を確認してください。\n' + result.errors.join('\n');
    el('messages').hidden = false;
    return;
  }
  el('total-wage').textContent = yen(result.units);
  el('total-time').textContent = SalaryCalculator.formatTime(result.minutes);
  el('total-days').textContent = `${result.days}日`;
  el('daily-results').replaceChildren();
  const grouped = new Map();
  for (const shift of result.shifts) {
    if (!grouped.has(shift.key)) grouped.set(shift.key, []);
    grouped.get(shift.key).push(shift);
  }
  for (const [key, shifts] of grouped) {
    const first = shifts[0], day = node('article', undefined, 'day');
    const heading = node('div', undefined, 'day-heading');
    const title = node('strong', `${key.replaceAll('-', '/')}（${'日月火水木金土'[first.date.getUTCDay()]}）`);
    if (first.special) title.append(node('span', first.holiday || '土日', 'badge'));
    heading.append(title, node('strong', yen(shifts.reduce((sum, shift) => sum + shift.units, 0))));
    day.append(heading);
    for (const shift of shifts) {
      day.append(node('p', `${clock(shift.start)}〜${clock(shift.end)} · ${SalaryCalculator.formatTime(shift.end - shift.start)}`));
      day.append(node('p', shift.breakdown.map(b => `${b.label}：${SalaryCalculator.formatTime(b.minutes)} × ${b.rate.toLocaleString('ja-JP')}円`).join(' / ')));
    }
    el('daily-results').append(day);
  }
  el('results').hidden = false;
  el('result-title').tabIndex = -1;
  el('result-title').focus();
});
