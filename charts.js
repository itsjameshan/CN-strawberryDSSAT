// assets/charts.js — Crop Growth Simulation Dynamic Demo
(function () {
  'use strict';

  // ── Colors (dark theme) ──
  var C = {
    accent:  '#38bdf8',
    accent2: '#a78bfa',
    green:   '#4ade80',
    red:     '#f87171',
    orange:  '#fb923c',
    magenta: '#e879f9',
    yellow:  '#fbbf24',
    ink:     '#f1f5f9',
    muted:   '#94a3b8',
    rule:    '#334155',
    bg2:     '#1e293b',
    bg:      '#0f172a'
  };

  // ── Simulate 350 days of data ──
  var TOTAL_DAYS = 350;
  var DAYS = [];
  for (var i = 0; i <= TOTAL_DAYS; i++) DAYS.push(i);

  // Helper: logistic / sigmoid
  function sigmoid(x, mid, steep, lo, hi) {
    return lo + (hi - lo) / (1 + Math.exp(-steep * (x - mid)));
  }
  // Helper: clamp
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  // ── Biomass data (g/plant) ──
  function genBiomass(d) {
    var total = sigmoid(d, 90, 0.06, 0.060, 0.105);
    var leaves = sigmoid(d, 70, 0.08, 0.010, 0.035);
    var stems  = sigmoid(d, 100, 0.05, 0.005, 0.020);
    var roots  = sigmoid(d, 50, 0.10, 0.012, 0.025);
    var fruits = sigmoid(d, 80, 0.07, 0.000, 0.020);
    return { total: +total.toFixed(5), leaves: +leaves.toFixed(5), stems: +stems.toFixed(5), roots: +roots.toFixed(5), fruits: +fruits.toFixed(5) };
  }

  // ── LAI ──
  function genLAI(d) {
    var base = sigmoid(d, 60, 0.06, 0.00047, 0.00062);
    var dip  = 0.00012 * Math.exp(-0.005 * Math.pow(d - 70, 2));
    return +(base - dip + 0.00009 * (d / 350)).toFixed(5);
  }

  // ── Fruit count ──
  function genFruitCount(d) {
    if (d < 55) return 0;
    return +sigmoid(d, 65, 0.15, 0, 48).toFixed(0);
  }

  // ── Crown & stolon ──
  function genCrownStolon(d) {
    var crown = sigmoid(d, 60, 0.06, 1.0, 2.3);
    var stolon = sigmoid(d, 40, 0.08, 0, 4.5);
    return { crown: +crown.toFixed(2), stolon: +stolon.toFixed(2) };
  }

  // ── Water stress ──
  function genWaterStress(d) {
    // pseudo-random oscillation based on day
    var base = 0.10 + 0.08 * Math.sin(d * 0.12) + 0.05 * Math.sin(d * 0.31) + 0.03 * Math.cos(d * 0.53);
    var envelope = sigmoid(d, 250, 0.02, 1.0, 0.6);
    return +clamp(base * envelope, 0.01, 0.35).toFixed(3);
  }

  // ── Phenology stages ──
  var PHENO_STAGES = [
    { name: '发芽期',     start: 0,   end: 10,  level: 0 },
    { name: '出苗期',     start: 10,  end: 20,  level: 1 },
    { name: '幼苗期',     start: 20,  end: 30,  level: 2 },
    { name: '营养生长期', start: 30,  end: 45,  level: 3 },
    { name: '花芽分化期', start: 45,  end: 55,  level: 4 },
    { name: '开花期',     start: 55,  end: 65,  level: 5 },
    { name: '坐果期',     start: 65,  end: 80,  level: 6 },
    { name: '果实发育期', start: 80,  end: 120, level: 7 },
    { name: '果实成熟期', start: 120, end: 140, level: 8 },
    { name: '衰老期',     start: 140, end: 350, level: 9 }
  ];

  function getPhenology(d) {
    for (var i = PHENO_STAGES.length - 1; i >= 0; i--) {
      if (d >= PHENO_STAGES[i].start) return PHENO_STAGES[i];
    }
    return PHENO_STAGES[0];
  }

  // ── Pre-generate full data arrays ──
  var biomassData = { total: [], leaves: [], stems: [], roots: [], fruits: [] };
  var laiData = [];
  var fruitCountData = [];
  var crownData = [];
  var stolonData = [];
  var waterData = [];

  for (var d = 0; d <= TOTAL_DAYS; d++) {
    var b = genBiomass(d);
    biomassData.total.push(b.total);
    biomassData.leaves.push(b.leaves);
    biomassData.stems.push(b.stems);
    biomassData.roots.push(b.roots);
    biomassData.fruits.push(b.fruits);
    laiData.push(genLAI(d));
    fruitCountData.push(genFruitCount(d));
    var cs = genCrownStolon(d);
    crownData.push(cs.crown);
    stolonData.push(cs.stolon);
    waterData.push(genWaterStress(d));
  }

  // ── Chart shared config ──
  var axisLineCfg = { lineStyle: { color: C.rule } };
  var splitLineCfg = { lineStyle: { color: C.rule, type: 'dashed' } };

  function makeChart(elId) {
    return echarts.init(document.getElementById(elId), null, { renderer: 'svg' });
  }

  // ── 1. Biomass chart ──
  var chartBiomass = makeChart('chart-biomass');
  function optionBiomass(endDay) {
    var ed = clamp(endDay, 0, TOTAL_DAYS);
    return {
      animation: false,
      grid: { top: 10, right: 14, bottom: 28, left: 58 },
      tooltip: { trigger: 'axis', appendToBody: true,
        textStyle: { color: C.ink, fontSize: 11 },
        backgroundColor: C.bg2, borderColor: C.rule },
      legend: { top: 0, textStyle: { color: C.muted, fontSize: 10 }, itemWidth: 14, itemHeight: 8 },
      xAxis: { type: 'category', data: DAYS.slice(0, ed + 1),
        axisLabel: { color: C.muted, fontSize: 9 }, axisLine: axisLineCfg, axisTick: { show: false },
        splitLine: splitLineCfg },
      yAxis: { type: 'value', min: 0, max: 0.11,
        axisLabel: { color: C.muted, fontSize: 9 }, axisLine: axisLineCfg,
        splitLine: splitLineCfg },
      series: [
        { name: '总生物量', type: 'line', data: biomassData.total.slice(0, ed + 1), symbol: 'none', lineStyle: { width: 2, color: C.accent }, itemStyle: { color: C.accent } },
        { name: '叶片',     type: 'line', data: biomassData.leaves.slice(0, ed + 1), symbol: 'none', lineStyle: { width: 1.5, color: C.green }, itemStyle: { color: C.green } },
        { name: '茎秆',     type: 'line', data: biomassData.stems.slice(0, ed + 1),  symbol: 'none', lineStyle: { width: 1.5, color: C.ink },  itemStyle: { color: C.ink } },
        { name: '根系',     type: 'line', data: biomassData.roots.slice(0, ed + 1),  symbol: 'none', lineStyle: { width: 1.5, color: C.orange }, itemStyle: { color: C.orange } },
        { name: '果实',     type: 'line', data: biomassData.fruits.slice(0, ed + 1), symbol: 'none', lineStyle: { width: 1.5, color: C.magenta }, itemStyle: { color: C.magenta } }
      ]
    };
  }
  chartBiomass.setOption(optionBiomass(0));

  // ── 2. LAI chart ──
  var chartLAI = makeChart('chart-lai');
  function optionLAI(endDay) {
    var ed = clamp(endDay, 0, TOTAL_DAYS);
    var data = laiData.slice(0, ed + 1);
    // find min/max for auto-scale
    var minV = Math.min.apply(null, data);
    var maxV = Math.max.apply(null, data);
    var pad = (maxV - minV) * 0.15 || 0.00005;
    return {
      animation: false,
      grid: { top: 10, right: 14, bottom: 28, left: 58 },
      tooltip: { trigger: 'axis', appendToBody: true,
        textStyle: { color: C.ink, fontSize: 11 },
        backgroundColor: C.bg2, borderColor: C.rule },
      xAxis: { type: 'category', data: DAYS.slice(0, ed + 1),
        axisLabel: { color: C.muted, fontSize: 9 }, axisLine: axisLineCfg, axisTick: { show: false },
        splitLine: splitLineCfg },
      yAxis: { type: 'value', min: minV - pad, max: maxV + pad,
        axisLabel: { color: C.muted, fontSize: 9, formatter: function(v) { return v.toFixed(5); } },
        axisLine: axisLineCfg, splitLine: splitLineCfg },
      series: [{ type: 'line', data: data, symbol: 'none', lineStyle: { width: 2, color: C.green }, areaStyle: { color: C.green, opacity: 0.15 }, itemStyle: { color: C.green } }]
    };
  }
  chartLAI.setOption(optionLAI(0));

  // ── 3. Fruit count ──
  var chartFruit = makeChart('chart-fruit');
  function optionFruit(endDay) {
    var ed = clamp(endDay, 0, TOTAL_DAYS);
    return {
      animation: false,
      grid: { top: 10, right: 14, bottom: 28, left: 40 },
      tooltip: { trigger: 'axis', appendToBody: true,
        textStyle: { color: C.ink, fontSize: 11 },
        backgroundColor: C.bg2, borderColor: C.rule },
      xAxis: { type: 'category', data: DAYS.slice(0, ed + 1),
        axisLabel: { color: C.muted, fontSize: 9 }, axisLine: axisLineCfg, axisTick: { show: false },
        splitLine: splitLineCfg },
      yAxis: { type: 'value', min: 0, max: 55,
        axisLabel: { color: C.muted, fontSize: 9 }, axisLine: axisLineCfg,
        splitLine: splitLineCfg },
      series: [{ type: 'line', data: fruitCountData.slice(0, ed + 1), symbol: 'none', lineStyle: { width: 2, color: C.magenta }, areaStyle: { color: C.magenta, opacity: 0.12 }, itemStyle: { color: C.magenta } }]
    };
  }
  chartFruit.setOption(optionFruit(0));

  // ── 4. Crown & Stolon ──
  var chartCrown = makeChart('chart-crown');
  function optionCrown(endDay) {
    var ed = clamp(endDay, 0, TOTAL_DAYS);
    return {
      animation: false,
      grid: { top: 10, right: 14, bottom: 28, left: 40 },
      tooltip: { trigger: 'axis', appendToBody: true,
        textStyle: { color: C.ink, fontSize: 11 },
        backgroundColor: C.bg2, borderColor: C.rule },
      legend: { top: 0, textStyle: { color: C.muted, fontSize: 10 }, itemWidth: 14, itemHeight: 8 },
      xAxis: { type: 'category', data: DAYS.slice(0, ed + 1),
        axisLabel: { color: C.muted, fontSize: 9 }, axisLine: axisLineCfg, axisTick: { show: false },
        splitLine: splitLineCfg },
      yAxis: { type: 'value', min: 0, max: 5,
        axisLabel: { color: C.muted, fontSize: 9 }, axisLine: axisLineCfg,
        splitLine: splitLineCfg },
      series: [
        { name: '冠数',     type: 'line', data: crownData.slice(0, ed + 1),  symbol: 'none', lineStyle: { width: 2, color: C.accent }, itemStyle: { color: C.accent } },
        { name: '匍匐茎数', type: 'line', data: stolonData.slice(0, ed + 1), symbol: 'none', lineStyle: { width: 2, color: C.red },    itemStyle: { color: C.red } }
      ]
    };
  }
  chartCrown.setOption(optionCrown(0));

  // ── 5. Water stress ──
  var chartWater = makeChart('chart-water');
  function optionWater(endDay) {
    var ed = clamp(endDay, 0, TOTAL_DAYS);
    return {
      animation: false,
      grid: { top: 10, right: 14, bottom: 28, left: 40 },
      tooltip: { trigger: 'axis', appendToBody: true,
        textStyle: { color: C.ink, fontSize: 11 },
        backgroundColor: C.bg2, borderColor: C.rule },
      xAxis: { type: 'category', data: DAYS.slice(0, ed + 1),
        axisLabel: { color: C.muted, fontSize: 9 }, axisLine: axisLineCfg, axisTick: { show: false },
        splitLine: splitLineCfg },
      yAxis: { type: 'value', min: 0, max: 0.35,
        axisLabel: { color: C.muted, fontSize: 9 }, axisLine: axisLineCfg,
        splitLine: splitLineCfg },
      series: [{ type: 'line', data: waterData.slice(0, ed + 1), symbol: 'none', lineStyle: { width: 1.2, color: C.red }, itemStyle: { color: C.red } }]
    };
  }
  chartWater.setOption(optionWater(0));

  // ── 6. Phenology chart ──
  var chartPheno = makeChart('chart-pheno');
  function optionPheno(endDay) {
    var ed = clamp(endDay, 0, TOTAL_DAYS);
    var categories = PHENO_STAGES.map(function(s) { return s.name; });
    // build data: one point per stage transition that has occurred
    var seriesData = [];
    for (var s = 0; s < PHENO_STAGES.length; s++) {
      var stg = PHENO_STAGES[s];
      if (ed >= stg.start) {
        var endPt = Math.min(ed, stg.end);
        // We'll add a single point at the midpoint of the active range for current stage
        var mid = Math.floor((stg.start + endPt) / 2);
        seriesData.push([mid, stg.level]);
      }
    }
    // Actually, let's do a step chart approach
    // Build step data: for each day 0..ed, what level
    var stepData = [];
    for (var dd = 0; dd <= ed; dd++) {
      stepData.push([dd, getPhenology(dd).level]);
    }
    return {
      animation: false,
      grid: { top: 10, right: 14, bottom: 28, left: 72 },
      tooltip: { trigger: 'axis', appendToBody: true,
        textStyle: { color: C.ink, fontSize: 11 },
        backgroundColor: C.bg2, borderColor: C.rule,
        formatter: function(params) {
          var day = params[0].data[0];
          var stage = getPhenology(day);
          return '第 ' + day + ' 天: ' + stage.name;
        }
      },
      xAxis: { type: 'value', min: 0, max: TOTAL_DAYS,
        axisLabel: { color: C.muted, fontSize: 9 }, axisLine: axisLineCfg,
        splitLine: splitLineCfg },
      yAxis: { type: 'category', data: categories,
        axisLabel: { color: C.muted, fontSize: 9 }, axisLine: axisLineCfg,
        splitLine: splitLineCfg },
      series: [{
        type: 'line', data: stepData, symbol: 'none',
        lineStyle: { width: 2.5, color: C.accent },
        itemStyle: { color: C.accent },
        step: 'middle'
      }]
    };
  }
  chartPheno.setOption(optionPheno(0));

  // ── Resize ──
  window.addEventListener('resize', function () {
    chartBiomass.resize();
    chartLAI.resize();
    chartFruit.resize();
    chartCrown.resize();
    chartWater.resize();
    chartPheno.resize();
  });

  // ── Animation engine ──
  var currentDay = 0;
  var playing = false;
  var speed = 3; // days per frame
  var animTimer = null;
  var frameInterval = 50; // ms per frame

  var elDayNum     = document.getElementById('day-num');
  var elPhenoText  = document.getElementById('phenology-text');
  var elStatBio    = document.getElementById('stat-biomass');
  var elStatLAI    = document.getElementById('stat-lai');
  var elStatFruit  = document.getElementById('stat-fruit');
  var elStatCrown  = document.getElementById('stat-crown');
  var elStatStolon = document.getElementById('stat-stolon');
  var btnPlay  = document.getElementById('btn-play');
  var btnPause = document.getElementById('btn-pause');
  var btnReset = document.getElementById('btn-reset');
  var speedSlider = document.getElementById('speed-slider');
  var speedVal = document.getElementById('speed-val');

  function updateDisplay() {
    var d = clamp(currentDay, 0, TOTAL_DAYS);
    elDayNum.textContent = d;

    var pheno = getPhenology(d);
    elPhenoText.textContent = pheno.name;

    // color phenology label based on stage
    var stageColors = ['#fbbf24','#fbbf24','#4ade80','#4ade80','#a78bfa','#e879f9','#e879f9','#f87171','#f87171','#94a3b8'];
    elPhenoText.style.background = stageColors[pheno.level] || C.accent;

    // Stats
    var b = genBiomass(d);
    elStatBio.textContent = b.total.toFixed(3);
    elStatLAI.textContent = genLAI(d).toFixed(5);
    elStatFruit.textContent = genFruitCount(d);
    var cs = genCrownStolon(d);
    elStatCrown.textContent = cs.crown.toFixed(1);
    elStatStolon.textContent = cs.stolon.toFixed(1);

    // Update charts
    chartBiomass.setOption(optionBiomass(d), true);
    chartLAI.setOption(optionLAI(d), true);
    chartFruit.setOption(optionFruit(d), true);
    chartCrown.setOption(optionCrown(d), true);
    chartWater.setOption(optionWater(d), true);
    chartPheno.setOption(optionPheno(d), true);
  }

  function tick() {
    if (!playing) return;
    currentDay += speed;
    if (currentDay > TOTAL_DAYS) {
      currentDay = TOTAL_DAYS;
      playing = false;
      btnPlay.classList.remove('active');
    }
    updateDisplay();
    if (playing) {
      animTimer = setTimeout(tick, frameInterval);
    }
  }

  btnPlay.addEventListener('click', function () {
    if (playing) return;
    if (currentDay >= TOTAL_DAYS) currentDay = 0;
    playing = true;
    btnPlay.classList.add('active');
    btnPause.classList.remove('active');
    tick();
  });

  btnPause.addEventListener('click', function () {
    playing = false;
    btnPlay.classList.remove('active');
    btnPause.classList.add('active');
    if (animTimer) clearTimeout(animTimer);
  });

  btnReset.addEventListener('click', function () {
    playing = false;
    if (animTimer) clearTimeout(animTimer);
    currentDay = 0;
    btnPlay.classList.remove('active');
    btnPause.classList.remove('active');
    updateDisplay();
  });

  speedSlider.addEventListener('input', function () {
    speed = parseInt(this.value);
    speedVal.textContent = speed + 'x';
  });

  // ── Initial render ──
  updateDisplay();

})();
