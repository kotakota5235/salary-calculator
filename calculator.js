/* Integer minute × hourly-rate totals avoid floating-point accumulation. */
(function (root) {
  'use strict';
  const pad = value => String(value).padStart(2, '0');
  const time = value => {
    const match = /^(\d{1,2}):(\d{2})$/.exec(value);
    if (!match) throw new Error('時刻は HH:MM で入力してください。');
    const hour = Number(match[1]), minute = Number(match[2]);
    if (minute > 59 || hour > 24 || (hour === 24 && minute !== 0)) throw new Error('時刻の範囲が正しくありません。');
    return hour * 60 + minute;
  };
  const formatTime = minutes => `${Math.floor(minutes / 60)}時間${minutes % 60 ? `${minutes % 60}分` : ''}`;
  function calculate(text, defaultYear, holidays) {
    const errors = [], shifts = [];
    if (!Number.isInteger(defaultYear) || defaultYear < holidays.minYear || defaultYear > holidays.maxYear) {
      return { errors: [`勤務年は${holidays.minYear}〜${holidays.maxYear}年で指定してください。`] };
    }
    text.split(/\r?\n/).forEach((raw, index) => {
      const line = raw.normalize('NFKC').trim();
      if (!line || /^日付\s+勤務時間/.test(line)) return;
      try {
        const match = /^(?:(\d{4})\/)?(\d{1,2})\/(\d{1,2})(?:\s*\([^)]*\))?\s+(.+)$/.exec(line);
        if (!match) throw new Error('日付と勤務時間を読み取れません。入力例を確認してください。');
        const [, y, m, d, rest] = match;
        if (/^(?:[-ー−―—]+|休み|公休|休日)(?:\s.*)?$/.test(rest)) return;
        const year = y ? Number(y) : defaultYear, month = Number(m), day = Number(d);
        const date = new Date(Date.UTC(year, month - 1, day));
        if (year < holidays.minYear || year > holidays.maxYear) throw new Error('この年の祝日データがありません。');
        if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) throw new Error('存在しない日付です。');
        const times = /^(\d{1,2}:\d{2})\s*[~〜～−–—ー-]\s*(\d{1,2}:\d{2})(?:\s+(\d{1,2}:\d{2})\s+(\d{1,2}:\d{2}))?\s*$/.exec(rest);
        if (!times) throw new Error('勤務時間は「17:00～20:00」の形式で入力してください。');
        const start = time(times[1]), end = time(times[2]);
        if (end <= start) throw new Error('終了時刻は開始より後にしてください。日をまたぐ勤務は24:00で行を分けてください。');
        if (times[4] && time(times[4]) !== 0) throw new Error('休憩があります。休憩を除いた勤務区間を別々の行に入力してください。');
        if (times[3] && time(times[3]) !== end - start) throw new Error('労働時間が開始・終了時刻と一致しません。');
        const key = `${year}-${pad(month)}-${pad(day)}`;
        if (shifts.some(s => s.key === key && s.start < end && start < s.end)) throw new Error('同じ日の勤務時間が重複しています。');
        const holiday = holidays.dates[key] || '';
        const special = Boolean(holiday) || [0, 6].includes(date.getUTCDay());
        const bands = special ? [[0, 1440, 1290, '土日祝']] : [[0, 780, 1140, '13:00より前'], [780, 1020, 1190, '13:00〜17:00'], [1020, 1440, 1290, '17:00以降']];
        const breakdown = bands.map(([from, to, rate, label]) => ({minutes: Math.max(0, Math.min(end, to) - Math.max(start, from)), rate, label})).filter(b => b.minutes);
        shifts.push({key, date, start, end, holiday, special, breakdown, units: breakdown.reduce((sum, b) => sum + b.minutes * b.rate, 0)});
      } catch (error) { errors.push(`${index + 1}行目：${error.message}`); }
    });
    if (errors.length) return {errors};
    if (!shifts.length) return {errors: ['計算できるシフトがありません。勤務のある行を入力してください。']};
    shifts.sort((a, b) => a.key.localeCompare(b.key) || a.start - b.start);
    return {errors, shifts, units: shifts.reduce((sum, s) => sum + s.units, 0), minutes: shifts.reduce((sum, s) => sum + s.end - s.start, 0), days: new Set(shifts.map(s => s.key)).size};
  }
  root.SalaryCalculator = {calculate, formatTime};
})(globalThis);
