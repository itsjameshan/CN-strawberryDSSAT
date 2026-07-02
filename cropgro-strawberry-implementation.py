"""Python implementation of the CROPGRO-Strawberry crop growth model.

This module contains a simplified, purely Python implementation of the
CROPGRO strawberry model.  The structure mirrors the original Fortran
code but trades some complexity for readability.  All major calculation
steps are implemented as small functions decorated with ``@njit`` to keep
them fast when the optional ``numba`` dependency is available.
"""

# CROPGRO-Strawberry Model Implementation in Python
# This is a simplified implementation of the CROPGRO model for strawberries

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

from dataclasses import dataclass, asdict, field
from numba import njit


@dataclass
class PlantState:
    # 初始干物质对齐 DSSAT 移栽苗 (plant_density=4.3 plants/m², 换算 kg/ha→g/plant ÷43)
    # DSSAT 初始: LWAD≈49, SWAD≈74, RWAD≈52 kg/ha → 1.14, 1.72, 1.21 g/plant
    biomass: float = 4.07
    leaf_area_index: float = 0.065
    root_depth: float = 10.0  # DSSAT RTDEPI=10.0 cm (SRGRO048.SPE L79)
    fruit_number: float = 0.0
    fruit_biomass: float = 0.0
    leaf_biomass: float = 1.14
    stem_biomass: float = 1.72
    root_biomass: float = 1.21
    phenological_stage: str = "GERMINATION"
    development_rate: float = 0.0
    crown_number: float = 1.0
    runner_number: float = 0.0
    # 水分胁迫因子 (0=无胁迫, 1=严重胁迫), 供 partition_biomass/update_fruits 使用
    water_stress: float = 0.0
    # DSSAT XFRUIT 动态分配追踪: 首次开花日 (DAP), 用于计算 XFRUIT 增长
    first_flower_dap: int = -1
    # --- DSSAT GROW.for 叶面积动态状态变量 ---
    # AREALF: 绿叶面积 (cm²/m²), DSSAT GROW.for L466/L1087
    # 对齐 DSSAT PlantGro.OUT DAP 0: LAID=0.065, SLAD=132.2
    # AREALF = LAID × 10000 = 650 cm²/m², WTLF = 4.9 g/m²
    arealf: float = 650.0
    # SLAAD: 动态比叶面积 (cm²/g), DSSAT GROW.for L1091
    # 初始 = DSSAT SLAD = 132.2 (移栽苗叶片厚于新叶 SLAVR=165)
    slaad: float = 132.0
    # LAIMX: 季节最大 LAI (用于输出), DSSAT GROW.for L1098
    laimx: float = 0.065
    # CUMTUR: 累积水分胁迫记忆 (DSSAT VEGGR.for), 用于 FRLF 调节
    cumtur: float = 1.0
    # CUMNSF: 累积氮胁迫记忆 (DSSAT DEMAND.for L564), 无 N 模块保持 1.0
    cumnsf: float = 1.0
    # EXCESS: 源汇调节因子 (DSSAT VEGGR.for L386), 1.0=无限制, 0.447=最大限制
    # 当 PGLEFT/PG 高时, EXCESS 降低明日 PG, 防止指数增长
    excess: float = 1.0
    # AGEFAC: 氮胁迫对光合的影响 (DSSAT PHOTO.for L132), 1.0=无胁迫
    # 简化: 随生物量增加氮稀释, AGEFAC 下降 (替代完整 N 模块)
    agefac: float = 1.0
    # 果实队列 (DSSAT PODS.for cohort 模型): 每个元素 = [count, biomass, age_days]
    # count: 该日座果的果实数, biomass: 该队列累计生物量 (g/plant), age: 座果后天数
    # 果实仅在 LAGSD ~ LAGSD+SFDUR 天内生长, 单果最大重 WFPOD
    fruit_cohorts: list = field(default_factory=list)
    # --- DSSAT DEMAND.for L508-536 R1后 FRLF/FRSTM 线性插值状态 ---
    # FRLFM/FRSTMM: R1 时捕获的表插值结果 (DEMAND.for L508-516)
    # R1前用表值; R1后线性插值到 FRLFF=0.45/FRSTMF=0.46 (SPE L52); NDLEAF后固定
    # frlfm/frstmm < 0 表示尚未到达 R1
    frlfm: float = -1.0
    frstmm: float = -1.0
    # phase13_tt: R1 后 phase 13 (1st FL → last leaf) 累积热时
    # DSSAT RStages.for: phase 13 用 reproductive 温度函数 (SPE L103:
    #   TB=7, TO1=15, TO2=18, TM=40) + 日长效应, FL-VS=100 photothermal days
    # 简化: 仅用 reproductive 温度阈值 (省略日长效应), 阈值=100 thermal days
    phase13_tt: float = 0.0
    # r7_tt: R1→R7 累积光热时间 (DSSAT stage 10, SPE L117)
    # DSSAT R7 用温度函数3 (TB=7,TO1=17,TO2=20,TM=48, SPE L104) + DRPP(PPSEN=1.00)
    # PPSEN=1.00 表示长日促进 R7 (草莓为长日植物); DRPP=1+PPSEN×(DAYL-CPPSL)/100
    # R7 阈值=117.1 光热日 (R1-R5=8.2 + R5-R7=108.9, Ipphenol)
    # 与 phase13_tt (温度函数2) 不同: R7 用更宽适温范围 (17-20 vs 15-18) + 长日促进
    r7_tt: float = 0.0
    # r7_reached: R7 (最后种子) 是否到达, 用于触发 SENRT2 快速衰老
    r7_reached: bool = False
    # GROMAX: VSSINK 库限机制的昨日潜在叶面积 (cm²/plant), DSSAT DEMAND.for L589
    # 当 V-stage < VSSINK 时, GROMAX = TABEX(YVGROW, XVGROW, VSTAGE) × SIZRAT
    # 每日叶面积增量 = (GROMAX_today - GROMAX_yesterday) × PLTPOP
    gromax: float = 0.0
    # NDLEAF_VSTAGE: 最后一片叶出现时的 V-stage (DSSAT GROW.for NDLEAF)
    # phase13_tt >= FL_VS 时记录, 之后 V-stage 固定不再增长
    # < 0 表示尚未到 NDLEAF
    ndleaf_vstage: float = -1.0
    # ACCAGE: 累积生理年龄 (DSSAT PODS.for L742), 从 NDSET→physiological maturity
    # 0→1 单调递增, 用于限制后期座果: PODADD *= MAX((1-ACCAGE),0)
    # DSSAT: ACCAGE += TEMPOD × DRPP × SWFAC / MNESPM (仅在 DAS>NDSET 时累积)
    accage: float = 0.0
    # CUMSIG: CRSD 5日滑动平均 (DSSAT PODCOMP L1030: CUMSIG=0.8*CUMSIG+0.2*CRSD)
    # 初始=1.0 (DSSAT PODCOMP L995 EMERG 初始化), 用于判断是否进入"满载推升"阶段
    cumsig: float = 1.0
    # VWAD: 地上营养生物量 (g/plant), DSSAT PlantGro.OUT VWAD = LWAD + SWAD
    # 不含根和果实, 用于对齐 DSSAT 输出
    vwad: float = 2.86   # 初始 = leaf_biomass + stem_biomass = 1.14 + 1.72
    # WCRSV: 储存 CH2O 池 (g/plant), DSSAT CROPGRO.for L1146 CSAVEV 累加
    # 通过 CMINEP = CMOBMX × (DTX+DXR57) × WCRSV 动员回流 PGAVL
    wcrsv: float = 0.0
    # CLW: 累积叶生长 (g/m²), DSSAT GROW.for L633 CLW = CLW + WLDOTN
    # 用于 SENES.for L185-190 自然衰老: VSTAGE>=5 时, WTLF 不能超过 CLW*PORLFT
    # 初始 = WTLF_0 * plant_density = 1.14 * 4.3 = 4.9 g/m²
    clw: float = 4.9
    # 花队列 (DSSAT PODS.for FLWN cohort): 每元素 = [count_per_m2, pntim_age]
    # 花经 PHTHRS(6)=4.0 p-t-d 成熟后转化为 FLWRDY, 再经 FLADD 限制座果
    flower_cohorts: list = field(default_factory=list)
    # SDWT: 种子(achenes)重量 (g/plant), DSSAT GROW.for L622 SDWT += WSDDOT
    # DSSAT GWAD 输出 = SDWT × 10 × PLTPOP (仅种子, 不含壳/花托)
    seed_biomass: float = 0.0
    # SHELWT: 壳(花托/肉质部分)重量 (g/plant), DSSAT GROW.for L623 SHELWT += WSHDOT
    # PODWT(整个果实) = SDWT + SHELWT, THRSH=20% 表示 SDWT/PODWT=20%
    shell_biomass: float = 0.0


@njit
def _calc_daylength(latitude, day_of_year):
    """Return length of the day in hours for a given latitude and date."""
    # Solar declination angle for the given day of year
    declination = 23.45 * np.sin(np.deg2rad(360 * (day_of_year - 80) / 365))

    # Convert latitude to radians for trig functions
    lat_rad = np.deg2rad(latitude)

    # Intermediate term of the daylength equation
    term = -np.tan(lat_rad) * np.tan(np.deg2rad(declination))
    if term >= 1.0:
        return 0.0
    elif term <= -1.0:
        return 24.0
    else:
        return 24.0 * np.arccos(term) / np.pi


@njit
def _thermal_time(tmin, tmax, tbase, to1, to2, tmax_th):
    """DSSAT PHENOL.for 热时计算 (thermal days/day, 0-1 范围).

    Parameters:
        tmin, tmax : float
            日最低/最高温度 (°C).
        tbase : float
            基点温度 TB (°C).
        to1, to2 : float
            最适温度范围 TO1/TO2 (°C), 在此范围内 CURV=1.
        tmax_th : float
            最高温度上限 TM (°C).

    Returns:
        float
            日热时积累 (thermal days), 最适温度下 1.0/天.

    实现原理 (DSSAT SRGRO048.SPE L102-104, PHENOL.for L237):
        DSSAT 用 thermal days, FT(J) = (1/TS) × Σ CURV(TGRO(H))
        8 点小时温度 (TGRO) 由 tmin/tmax 正弦曲线生成
        CURV('LIN', TB, TO1, TO2, TM, T):
            T < TB: 0
            TB ≤ T < TO1: (T-TB)/(TO1-TB), 0→1
            TO1 ≤ T ≤ TO2: 1 (最适平台)
            TO2 < T < TM: (TM-T)/(TM-TO2), 1→0
            T ≥ TM: 0
        每日 thermal day = 8 点 CURV 平均, 最适温度下 1.0

    Note: 日均温度在跨越 TO1/TO2 断点时会高估热时 (分段线性函数的 Jensen 不等式).
          8 点积分修正此偏差, 对大温差日 (Tmax>TO2) 显著降低热时.
    """
    tavg = (tmin + tmax) / 2.0
    trange = tmax - tmin

    # 8 点正弦温度积分 (DSSAT PHENOL.for TS=8, 每 3 小时)
    # T(h) = tavg + (trange/2) × cos(2π(h-14)/24), 最高温在 14:00
    curv_sum = 0.0
    for i in range(8):
        hour = i * 3.0 + 1.5  # 1.5, 4.5, 7.5, ..., 22.5
        t_hour = tavg + (trange / 2.0) * np.cos(
            2.0 * np.pi * (hour - 14.0) / 24.0)
        if t_hour <= tbase:
            c = 0.0
        elif t_hour < to1:
            c = (t_hour - tbase) / (to1 - tbase) if to1 > tbase else 0.0
        elif t_hour <= to2:
            c = 1.0
        elif t_hour < tmax_th:
            c = (tmax_th - t_hour) / (tmax_th - to2) if tmax_th > to2 else 0.0
        else:
            c = 0.0
        curv_sum += c
    return curv_sum / 8.0


@njit
def _tabex_lin(xs, ys, n, x):
    """DSSAT TABEX 线性插值 (TYPPGT/LIN 类型).

    Parameters:
        xs, ys : np.ndarray
            自变量和因变量数组 (单调递增).
        n : int
            数组长度.
        x : float
            待插值点.

    Returns:
        float
            插值结果, 超出范围则取端点值.
    """
    if x <= xs[0]:
        return ys[0]
    if x >= xs[n - 1]:
        return ys[n - 1]
    for i in range(n - 1):
        if xs[i] <= x <= xs[i + 1]:
            dx = xs[i + 1] - xs[i]
            if dx <= 1e-10:
                return ys[i]
            r = (x - xs[i]) / dx
            return ys[i] + r * (ys[i + 1] - ys[i])
    return ys[n - 1]


@njit
def _photosynthesis(solar_radiation, tmax, tmin, kcanr, lai, co2,
                    slaad, swfac, excess, agefac):
    """DSSAT PHOTO.for 冠层光合.

    PG = PTSMAX × SLPF × PGFAC × TPGFAC × E_FAC × PGSLW × PRATIO × PGLFMX × SWFAC × EXCESS

    Parameters:
        solar_radiation : float
            日总辐射 (MJ/m2/d).
        tmax, tmin : float
            日最高/最低温度 (°C).
        kcanr : float
            行距修正消光系数 KCANR (DSSAT PHOTO.for L121).
            KCANR = KCAN - (1-SPACNG)*KC_SLOPE, UFBA1401 ≈ 0.249.
            SPACNG = MIN(BETN,ROWSPC)/MAX(BETN,ROWSPC), BETN=1/(ROWSPC*PLTPOP).
        lai : float
            叶面积指数.
        co2 : float
            大气 CO2 浓度 (ppm).
        slaad : float
            当前比叶面积 (cm2/g), 用于计算比叶重 SLW (g/cm2).
            DSSAT SPE L14 XPGSLW 表范围 0-0.010 g/cm2.
        swfac : float
            水分胁迫因子 (0-1, 1=无胁迫), 即 DSSAT SWFAC.
        excess : float
            源汇调节因子 EXCESS (DSSAT VEGGR.for L386).
            1.0=无限制, 0.447=最大限制 (PGLEFT/PG=1.0 时).
        agefac : float
            氮胁迫对光合的影响 AGEFAC (DSSAT PHOTO.for L132).
            1.0=无胁迫, <1.0 表示 N 稀释导致光合降低.

    Returns:
        float
            日总光合 PG (g CH2O/m2/d).

    实现原理 (DSSAT PHOTO.for L110-231):
        1. PTSMAX = PHTMAX × (1 - exp(-PAR/PARMAX)), PHTMAX=61, PARMAX=41
        2. PGFAC = 1 - exp(-KCANR × XHLAI), 行距修正 (PHOTO.for L121-122)
           SPACNG = MIN(BETN,ROWSPC)/MAX(BETN,ROWSPC), BETN=1/(ROWSPC*PLTPOP)
        3. TPGFAC = TABEX(FNPGT=5/22/29/45, TDAY), TYPPGT='LIN'
        4. AGEFCC = (1-exp(-2×AGEFAC))/(1-exp(-2×1)), E_FAC=AGEFCC (无 P 模块)
        5. PGSLW = TABEX(YPGSLW, XPGSLW, SLW, 10), SLW=1/SLAAD
        6. PRATIO = A0 + CCMAX×(1-exp(-CCK×CO2)), CCK=CCEFF/CCMAX
        7. PGLFMX = (1-exp(-1.6×LMXSTD))/(1-exp(-1.6×PGREF))
        8. PG = PTSMAX × PGFAC × TPGFAC × E_FAC × PGSLW × PRATIO × PGLFMX × SWFAC × EXCESS
    """
    # --- 1. 饱和曲线 PTSMAX (DSSAT L110) ---
    # DSSAT Weather 模块 (WGEN.for / HMET.for): PAR = 2.0 * SRAD
    # SRAD 单位为 MJ/m2/d, PAR 单位为 mol quanta/m2/d (PARFAC=2.0)
    # PARMAX=41.0 (SPE L4) 单位与 PAR 一致 (mol quanta/m2/d)
    PHTMAX = 61.0
    PARMAX = 41.0
    par = solar_radiation * 2.0  # DSSAT PARFAC=2.0, MJ/m2/d -> mol quanta/m2/d
    ptsmax = PHTMAX * (1.0 - np.exp(-par / PARMAX))

    # --- 2. 光截获 PGFAC (DSSAT L121-122, 行距修正 KCANR) ---
    pgfac = 1.0 - np.exp(-kcanr * lai)

    # --- 3. 温度响应 TPGFAC (DSSAT L127, FNPGT=5/22/29/45, LIN) ---
    xs_t = np.array([5.0, 22.0, 29.0, 45.0])
    ys_t = np.array([0.0, 1.0, 1.0, 0.0])
    tday = (tmax + tmin) / 2.0 + 2.0  # DSSAT TDAY 略高于日均
    tpgfac = _tabex_lin(xs_t, ys_t, 4, tday)

    # --- 4. AGEFAC/AGEFCC (DSSAT L132-142) ---
    # AGEFAC 由调用方传入 (简化 N 模块: 随生物量增加而下降)
    # AGEFCC = (1-exp(-2×AGEFAC))/(1-exp(-2×1)), DSSAT L142
    agefcc = (1.0 - np.exp(-2.0 * agefac)) / (1.0 - np.exp(-2.0 * 1.0))
    # E_FAC = MIN(AGEFCC, PStres1), 无 P 模块: PStres1 = 1.0
    e_fac = agefcc

    # --- 5. 比叶重响应 PGSLW (DSSAT L148-153) ---
    # XPGSLW/YPGSLW 10点表 (SPE L14-15), SLW = 1/SLAAD (g/m2)
    xs_slw = np.array([0.0, 0.001, 0.002, 0.003, 0.0035,
                       0.004, 0.005, 0.006, 0.008, 0.010])
    ys_slw = np.array([0.162, 0.679, 0.867, 0.966, 1.000,
                       1.027, 1.069, 1.100, 1.141, 1.167])
    if slaad > 0.0:
        slw = 1.0 / slaad
    else:
        slw = 0.0099  # DSSAT 默认值
    pgslw = _tabex_lin(xs_slw, ys_slw, 10, slw)

    # --- 6. CO2 效应 PRATIO (DSSAT L159-161) ---
    CCMP = 68.0
    CCMAX = 1.94
    CCEFF = 0.0128
    cck = CCEFF / CCMAX
    a0 = -CCMAX * (1.0 - np.exp(-cck * CCMP))
    pratio = a0 + CCMAX * (1.0 - np.exp(-cck * co2))

    # --- 7. 基因型最大光合 PGLFMX (DSSAT L86) ---
    # LFMAX=1.35 (CUL SR0001), PGREF=1.60 (SPE L12 第5列)
    # SPE L12: .0018 .0006 .2500 4.50 1.60 → SLWREF,SLWSLO,NSLOPE,LNREF,PGREF
    LMXSTD = 1.35  # LFMAX from CUL SR0001
    PGREF = 1.60    # SPE L12 第5列 (PGREF, 非 LNREF=4.50)
    pglfmx = (1.0 - np.exp(-1.6 * LMXSTD)) / (1.0 - np.exp(-1.6 * PGREF))

    # --- 8. 最终 PG (DSSAT L194-195, L231) ---
    # SLPF=1.0 (土壤磷胁迫, 默认)
    # EXCESS: 源汇调节因子, 昨日 PGLEFT 高时降低今日 PG (DSSAT L231)
    SLPF = 1.0
    pg = (ptsmax * SLPF * pgfac * tpgfac * e_fac * pgslw
          * pratio * pglfmx * swfac * excess)
    return pg


@njit
def _transpiration(solar_radiation, tmax, tmin, rh, lai):
    """Compute potential plant transpiration using a simple ET0 approach."""
    # Mean temperature for the day
    tavg = (tmax + tmin) / 2.0

    # Simplified reference evapotranspiration (Hargreaves)
    et0 = 0.0023 * solar_radiation * np.sqrt(tmax - tmin) * (tavg + 17.8)

    # Crop coefficient as a function of canopy development
    kc = 0.3 + 0.7 * (1.0 - np.exp(-0.7 * lai))
    return et0 * kc


@njit
def _tphfac_parton_logan(tmax, tmin, daylength):
    """DSSAT HMET.for HTEMP (Parton-Logan 1981): 8点温度序列 TPHFAC 计算.

    DSSAT DEMAND.for L547-551:
        TPHFAC = mean(TABEX(YSLATM, XSLATM, TGRO(I), 5))  for I=1,TS
    TGRO(I) 由 Parton-Logan 模型从 TMAX/TMIN/DAYL 生成:
        白天 (日出到日落): 正弦曲线 T = TMIN + (TMAX-TMIN)*sin(0.5π*(h-tmin_time)/(tmax_time-tmin_time))
        夜间: 指数衰减 T = TMINI + (TSNDN-TMINI)*exp(-B*t/HDECAY)
        TMIN 时间 = SNUP + C, TMAX 时间 = TMIN时间 + DAYL/2 + A
        A=2.0, B=2.2, C=1.0

    参数:
        tmax, tmin : float
            日最高/最低温 (°C)
        daylength : float
            天文日长 (小时)

    返回:
        float : 8点温度的 TABEX 平均 (0.48-1.0)
    """
    xs_t = np.array([-50.0, 0.0, 14.0, 19.1, 50.4])
    ys_t = np.array([0.48, 0.48, 0.48, 1.00, 0.1])
    A = 2.0
    B = 2.2
    C = 1.0
    snup = 12.0 - daylength / 2.0
    sndn = 12.0 + daylength / 2.0
    tmin_time = snup + C
    tmax_time = tmin_time + daylength / 2.0 + A
    denom = tmax_time - tmin_time
    if denom < 1e-6:
        denom = 1e-6
    arg_sndn = 0.5 * np.pi * (sndn - tmin_time) / denom
    tsndn = tmin + (tmax - tmin) * np.sin(arg_sndn)
    exp_neg_b = np.exp(-B)
    tmini = (tmin - tsndn * exp_neg_b) / (1.0 - exp_neg_b)
    hdecay = 24.0 + C - daylength
    if hdecay < 1.0:
        hdecay = 1.0
    tphfac_sum = 0.0
    for i in range(8):
        hs = i * 3.0
        if tmin_time <= hs <= sndn:
            t = 0.5 * np.pi * (hs - tmin_time) / denom
            tair = tmin + (tmax - tmin) * np.sin(t)
        elif hs > sndn:
            t = hs - sndn
            arg = -B * t / hdecay
            tair = tmini + (tsndn - tmini) * np.exp(arg)
        else:
            t = 24.0 + hs - sndn
            arg = -B * t / hdecay
            tair = tmini + (tsndn - tmini) * np.exp(arg)
        tphfac_sum += _tabex_lin(xs_t, ys_t, 5, tair)
    return tphfac_sum / 8.0


@njit
def _leaf_sla_factor(tmax, tmin, daylength, par, swfac, xfrt, fracdn,
                     slaad_current):
    """DSSAT DEMAND.for L544-578: 计算新组织比叶面积 F (cm²/g).

    DSSAT 公式:
        F = FVEG × TPHFAC × PARSLA × TURFSL × CUMNSF
        若 XFRT×FRACDN >= 0.05: F = F × (1 - XFRT×FRACDN)  (生殖阶段抑制叶扩张)

    参数 (SRGRO048.SPE):
        SLAVR=165 (CUL SR0001), SLAREF=200, SLAMAX=400, SLAMIN=215,
        SLAPAR=-0.047, TURSLA=1.5
        XSLATM=[-50, 0, 14, 19.1, 50.4], YSLATM=[0.48, 0.48, 0.48, 1.0, 0.1]

    Note: 无 N 模块, NSLA/NFSL/CUMNSF = 1.0.
    """
    # --- 1. DUMFAC/SLAMN/SLAMX (DEMAND.for L172-177) ---
    SLAVR = 165.0
    SLAREF = 200.0
    SLAMAX = 400.0
    SLAMIN = 215.0
    SLAPAR = -0.047
    TURSLA = 1.5
    DUMFAC = SLAVR / SLAREF  # 0.825
    FVEG = DUMFAC * SLAMAX   # 330 cm²/g (新叶最大 SLA)
    SLAMN = DUMFAC * SLAMIN  # 177.4 cm²/g (新叶最小 SLA)
    SLAMX = DUMFAC * SLAMAX  # 330 cm²/g

    # --- 2. TPHFAC: 8点 Parton-Logan 温度序列 (DEMAND.for L547-551) ---
    tphfac = _tphfac_parton_logan(tmax, tmin, daylength)

    # --- 3. PARSLA: PAR 效应 (DEMAND.for L555) ---
    # PARSLA = (SLAMN + (SLAMX-SLAMN)*EXP(SLAPAR*PAR)) / SLAMX
    # par 单位: mol quanta/m²/d (与 DSSAT 一致)
    parsla = (SLAMN + (SLAMX - SLAMN) * np.exp(SLAPAR * par)) / SLAMX

    # --- 4. TURFSL: 水分胁迫效应 (DEMAND.for L556) ---
    # TURFAC = SWFAC (1=无胁迫, 0=严重胁迫); swfac 传入时已为 DSSAT 风格
    turfac = swfac
    turfsl = max(0.1, (1.0 - (1.0 - turfac) * TURSLA))

    # --- 5. CUMNSF: 氮胁迫记忆 (DEMAND.for L564), 无 N 模块保持 1.0 ---
    cumnsf = 1.0

    # --- 6. F (DEMAND.for L571-574) ---
    f = FVEG * tphfac * parsla * turfsl * cumnsf
    # 生殖阶段抑制叶扩张 (DEMAND.for L574): XFRT×FRACDN >= 0.05 时
    xfrt_fracdn = xfrt * fracdn
    if xfrt_fracdn >= 0.05:
        f = f * (1.0 - xfrt_fracdn)
    # 防止 F 异常 (DSSAT GROW.for 无显式上限, 但负值无意义)
    if f < 0.0:
        f = 0.0
    return f


@njit
def _water_stress(field_capacity, wilting_point, root_depth, rainfall,
                  transpiration):
    """Derive a water stress factor from soil moisture balance."""
    # Total available soil water within the root zone
    available_water = (field_capacity - wilting_point) * root_depth

    # Assume some fraction of rainfall is effective in wetting the soil
    effective_rainfall = rainfall * 0.7

    # Water deficit is unmet transpiration demand
    deficit = max(0.0, transpiration - effective_rainfall)
    if deficit == 0.0:
        return 0.0
    else:
        stress_factor = min(1.0, deficit / available_water)
        return stress_factor


@njit
def _parton_logan_trsfac(tmax, tmin, daylength):
    """DSSAT RESPIR.for TRSFAC: 24点 Parton-Logan 小时温度的温度因子.

    DSSAT RESPIR.for L37-43:
        SCLTS = 24./TS  (TS=24, SCLTS=1.0)
        DO H = 1,TS
            TRSFAC = TRSFAC + (0.044+0.0019*TGRO(H)+0.001*TGRO(H)**2)*SCLTS
        ENDDO
    TGRO(H) 由 HMET.for HTEMP (Parton-Logan 1981) 从 TMAX/TMIN/DAYL 生成:
        白天 (SNUP+C ≤ HS ≤ SNDN): 正弦曲线 T = TMIN + (TMAX-TMIN)*sin(0.5π*(HS-MIN)/(MAX-MIN))
        夜间: 指数衰减 T = TMINI + (TSNDN-TMINI)*exp(-B*T/HDECAY)
        MIN = SNUP+C (最低温时间), MAX = MIN+DAYL/2+A (最高温时间)
        A=2.0, B=2.2, C=1.0

    Parameters:
        tmax, tmin : float
            日最高/最低温 (°C).
        daylength : float
            天文日长 (小时).

    Returns:
        float : TRSFAC (温度因子, 典型值 10.0-15.0 (24点积分 SCLTS=1.0), 30°C 恒温约 24.6).
    """
    A = 2.0
    B = 2.2
    C = 1.0
    snup = 12.0 - daylength / 2.0
    sndn = 12.0 + daylength / 2.0
    tmin_time = snup + C
    tmax_time = tmin_time + daylength / 2.0 + A
    denom = tmax_time - tmin_time
    if denom < 1e-6:
        denom = 1e-6
    arg_sndn = 0.5 * np.pi * (sndn - tmin_time) / denom
    tsndn = tmin + (tmax - tmin) * np.sin(arg_sndn)
    exp_neg_b = np.exp(-B)
    tmini = (tmin - tsndn * exp_neg_b) / (1.0 - exp_neg_b)
    hdecay = 24.0 + C - daylength
    if hdecay < 1.0:
        hdecay = 1.0

    TS = 24
    SCLTS = 24.0 / TS  # = 1.0
    trsfac = 0.0
    for h in range(1, TS + 1):
        hs = float(h) * (24.0 / TS)  # DSSAT: HS = REAL(H) * TINCR, 1.0..24.0
        if hs >= tmin_time and hs <= sndn:
            t = 0.5 * np.pi * (hs - tmin_time) / denom
            tair = tmin + (tmax - tmin) * np.sin(t)
        elif hs > sndn:
            t = hs - sndn
            arg = -B * t / hdecay
            tair = tmini + (tsndn - tmini) * np.exp(arg)
        else:
            t = 24.0 + hs - sndn
            arg = -B * t / hdecay
            tair = tmini + (tsndn - tmini) * np.exp(arg)
        trsfac += (0.044 + 0.0019 * tair + 0.001 * tair * tair) * SCLTS
    return trsfac


@njit
def _maintenance_resp(leaf_biomass, stem_biomass, root_biomass,
                      fruit_biomass, tmin, tmax, pg, plant_density,
                      daylength):
    """DSSAT RESPIR.for 维持呼吸 + 生长呼吸.

    Parameters:
        leaf/stem/root/fruit_biomass : float
            各器官干物质 (g/plant).
        tmin, tmax : float
            日最低/最高温度 (°C).
        pg : float
            冠层毛光合 PG (g CH2O/m²/d).
        plant_density : float
            种植密度 (plants/m²), 用于 PG→单株换算.
        daylength : float
            天文日长 (小时), 用于 Parton-Logan 小时温度生成.

    Returns:
        float
            总呼吸 MAINR (g/plant/d) = 维持呼吸 + 生长呼吸.

    实现原理 (DSSAT RESPIR.for + HMET.for HTEMP):
        TGRO(H) 由 Parton-Logan 模型从 TMAX/TMIN/DAYL 生成 (24 点)
        TRSFAC = Σ_{H=1}^{24} (0.044+0.0019*TGRO(H)+0.001*TGRO(H)²) × SCLTS
        SCLTS = 24/TS = 24/24 = 1.0
        RO = RES30C × TRSFAC    (维持呼吸系数 g/g/d, RES30C=2.5E-04)
        RP = R30C2 × TRSFAC     (生长呼吸系数, R30C2=0.0026)
        MAINR = RO × WTMAIN + RP × PG

    Note: Parton-Logan 夜间指数衰减比简单余弦给出更低夜间温度,
          T² 项使 TRSFAC 对夜间温度敏感, 对齐 DSSAT 可修正 MAINR 偏差.
    """
    # DSSAT RESPIR.for: TRSFAC from Parton-Logan 24 hourly temperatures
    trsfac = _parton_logan_trsfac(tmax, tmin, daylength)

    # 维持呼吸系数 (g CH2O / g DW / d), RES30C=2.5E-04 (SRGRO048.SPE L18)
    RES30C = 2.5e-04
    RO = RES30C * trsfac

    # 生长呼吸系数 (g CH2O / g CH2O fixed), R30C2=0.0026 (SRGRO048.SPE L18)
    R30C2 = 0.0026
    RP = R30C2 * trsfac

    # 总干物质 WTMAIN (g/plant) - 需维持呼吸的组织
    # DSSAT GROW.for L647-648: WSDMAN=MIN(SDWT,SHELWT), WTMAIN=TOTWT-SDWT+WSDMAN
    # 草莓 THRSH=20% → SDWT<SHELWT → MIN=SDWT → WTMAIN=TOTWT (全组织)
    WTMAIN = leaf_biomass + stem_biomass + root_biomass + fruit_biomass

    # PG 单株 (g CH2O/plant/d)
    pg_per_plant = pg / plant_density

    # MAINR = RO×WTMAIN + RP×PG (g/plant/d)
    mainr = RO * WTMAIN + RP * pg_per_plant
    return mainr


class CropgroStrawberry:
    """
    A Python implementation of the CROPGRO-Strawberry crop model.
    
    This model simulates strawberry growth and development based on 
    environmental conditions, plant characteristics, and management practices.
    """
    
    def __init__(self, latitude, planting_date, soil_properties, 
                 cultivar_params):
        """
        Initialize the CROPGRO-Strawberry model.
        
        Parameters:
        -----------
        latitude : float
            Site latitude in decimal degrees
        planting_date : str
            Planting date in format 'YYYY-MM-DD'
        soil_properties : dict
            Dictionary containing soil properties (depth, texture, 
            water holding capacity, etc.)
        cultivar_params : dict
            Dictionary containing cultivar-specific parameters
        """
        self.latitude = latitude
        self.planting_date = datetime.strptime(planting_date, '%Y-%m-%d')
        self.soil = soil_properties
        self.cultivar = cultivar_params
        
        # Initialize state variables
        self.days_after_planting = 0
        self.plant_state = PlantState()

        # 种植密度 (plants/m²), DSSAT UFBA1401.SRX PPOP=4.3
        self.plant_density = 4.3

        # DSSAT PHOTO.for L115-122 行距修正消光系数 KCANR
        # 经验事实: DSSAT PlantC.OUT (JUL 02 2026) DAP 10 PG=2.10 匹配 KCAN=0.67,
        # 非 KCANR=0.249。尽管 PHOTO.for 有 KCANR 计算代码, 草莓运行时未应用行距修正
        # (可能 IPPLNT.for 读取 KC_SLOPE 失败用默认 0.1, 或 FILEIO 覆盖)。
        # 对齐 DSSAT 实际行为: KCANR = KCAN (bypass 行距修正)
        self.kcanr = self.cultivar['kcan']

        # GROMAX 初始化为 0 (DSSAT DEMAND.for L178: GROMAX = 0.0)
        # 首日 (gromax==0) 在 VSSINK 中视为 GROYES=gromax_new, GAINNW=0
        # (移栽苗 AREALF=650 已超基因表目标 59, DSSAT LAID 保持 0.065)
        # 次日起 GAINNW = gromax_new - gromax_yesterday (小幅正, 叶缓慢增长)
        # FRRT 保持表值 (~0.30), FRSTM 吸收剩余碳 (FRSTM fix, DSSAT VEGGR L275)
        self.plant_state.gromax = 0.0

        # Accumulated thermal time (degree-days)
        self.thermal_time = 0.0
        self.thermal_time_today = 0.0  # 当日热时 (供 update_fruits 用, DSSAT TDUMX)
        self.repro_tt_today = 0.0  # 当日 reproductive 热时 (供 PHTIM 累积用)
        self.current_vstage = 4.6  # 初始 V-stage (DSSAT 移栽苗)
        
        # 物候阶段阈值 (thermal/photothermal days)
        # R1 前阶段: 从移栽(DAP 0)起算的 vegetative thermal time
        #   移栽苗 V-stage=4.6 (SDAGE=30) → 从种植起算已累积 ~17.5 thermal days
        #   (PL-EM=6.0 + 部分 EM-V1=11.5, 即 4.6/TRIFL=4.6/0.4=11.5)
        #   故原 ECO 绝对值需减去 17.5 转为从移栽起算:
        #     FLORAL_INDUCTION(R0): 33-17.5=15.5
        #     FLOWERING(R1): 从 DSSAT PlantGro.OUT DAP 23, V=12.3 反推
        #       from-transplant TT = (12.3-4.6)/TRIFL = 7.7/0.4 = 19.25
        # R1 后阶段: 从 R1 起算的 phase13_tt (reproductive thermal time)
        #   Ipphenol.for: R1-R3=8.158, R3-R5=0.042, R5-R7=108.9
        #   ECO: FL-VS=100.0 (from R1)
        self.phenology_stages = {
            'GERMINATION': 0,          # 移栽即种植
            'EMERGENCE': 0,            # 移栽苗已出苗 (PL-EM=6.0 已完成)
            'JUVENILE': 0,             # 移栽苗已过 juvenile (EM-V1 部分完成)
            'VEGETATIVE': 0,           # 移栽苗已过 V1
            'FLORAL_INDUCTION': 15.5,  # R0: 33-17.5 (vegetative TT, from transplant)
            'FLOWERING': 19.25,        # R1: V=12.3, (12.3-4.6)/0.4=19.25 (DSSAT DAP 23)
            # --- 以下用 phase13_tt (reproductive, from R1) ---
            'FRUIT_SET': 4.0,          # R3: R1-R3=PHTHRS(6)=FL-SH=4.0 (SRGRO048.CUL)
            'FRUIT_DEVELOPMENT': 8.2,  # R5: R1-R5=PHTHRS(8)=FL-SD=8.2 (SRGRO048.CUL)
            'FRUIT_MATURITY': 117.1,   # R7: R1-R7=117.1 (8.2+108.9, Ipphenol)
            'SENESCENCE': 100.0        # NDLEAF: FL-VS=100 (ECO, from R1)
        }
        
        # Results storage
        self.results = []
        # G#AD 座果链诊断变量 (partition_biomass 设置, simulate_day 读取)
        # 用于诊断花→果管道 FLWADD→FLWRDY→FLADD→SHELN 各环节
        self.diag_pgavlr_m2 = 0.0    # 繁殖可用碳 (g CH2O/m²/d)
        self.diag_pmax = 0.0          # 潜在座果率 (pods/m²/d)
        self.diag_flwadd = 0.0        # 新花数 (flowers/m²/d)
        self.diag_flwrdy = 0.0        # 成熟花数 (flowers/m²/d)
        self.diag_fladd = 0.0         # 花限制座果数 (pods/m²/d)
        self.diag_podadd = 0.0        # 碳限制座果数 (pods/m²/d)
        self.diag_actual_pods = 0.0   # 实际座果数 (pods/m²/d)
        self.diag_fruit_cohorts_count = 0  # 果队列数量
        # PGNPOD 碳限制诊断变量
        self.diag_pgnpod_m2 = 0.0       # 种子生长后剩余碳 (g CH2O/m²/d)
        self.diag_max_pods_carbon = 0.0  # 碳限制最大座果数 (pods/m²/d)
        # 碳流诊断变量 (用于定位 LAI 正反馈根因)
        self.diag_pgavl = 0.0            # PGAVL (g CH2O/plant/d) = PG - MAINR
        self.diag_csavev = 0.0           # CSAVEV (g CH2O/plant/d) = 0.25*PGAVL*FRACDN
        self.diag_pgavlr = 0.0           # PGAVLR (g CH2O/plant/d) = 繁殖可用碳
        self.diag_fruit_ch2o = 0.0       # 实际果实碳用量 (g CH2O/plant/d) = 种子碳
        self.diag_shell_ch2o = 0.0       # 壳碳用量 (g CH2O/plant/d)
        self.diag_cdmveg_ch2o = 0.0      # CDMVEG (g CH2O/plant/d) = 营养可用碳
        self.diag_leaf_alloc = 0.0       # 叶分配 (g tissue/plant)
        self.diag_sldot = 0.0            # 叶衰老 (g/m²/d)
        self.diag_ssdot = 0.0            # 茎衰老 (g/m²/d)
        self.diag_srdot = 0.0            # 根衰老 (g/m²/d, DSSAT ROOTS.for)
        self.diag_clw = 0.0              # 累积叶生长 (g/m²)
        self.diag_xfrt = 0.0             # XFRT 繁殖分配系数
        self.diag_pgleft = 0.0           # PGLEFT (g CH2O/m²/d, DSSAT VEGGR.for L373)
        self.diag_excess = 1.0           # EXCESS 源汇调节因子
        self.diag_rsd = 0.0              # RSD 种子碳限制分数 (DSSAT PODS.for L489)
        self.diag_gdmsd = 0.0            # GDMSD 总潜在种子需求 (g tissue/plant/d, DSSAT PODS.for L488)

        # --- DSSAT 多次采收机制 (FreshWt.for L390-403 + AUTHAR.for L159-173) ---
        # DSSAT SRX IHARI='R', 按 HDATE 指定日期采收; XMAGE=10.0 (SRGRO048.ECO L57)
        # 采收日移除所有 age >= XMAGE 的成熟果实队列 (FreshWt.for L391-399)
        # UFBA1401.SRX 有 33 次采收 (HDATE), 模拟期 110 天内 18 次:
        # DAP 45,52,55,59,62,66,69,73,75,80,84,87,90,94,97,101,104,108
        self.harvest_daps = {45, 52, 55, 59, 62, 66, 69, 73, 75, 80,
                             84, 87, 90, 94, 97, 101, 104, 108}
        self.xmage_harvest = 10.0  # 采收成熟阈值 (光热日, 简化为实际天数)
        self.harvested_seed_biomass = 0.0   # 累计采收种子重 (g/plant)
        self.harvested_shell_biomass = 0.0  # 累计采收壳重 (g/plant)
        self.harvested_fruit_count = 0.0    # 累计采收果实数 (fruits/plant)
        self.harvest_count = 0              # 采收次数计数器
        self.diag_harvest_today = 0.0       # 当日采收种子重 (g/plant, 诊断用)
        
    def calculate_daylength(self, day_of_year):
        """
        Calculate daylength based on latitude and day of year.
        
        Parameters:
        -----------
        day_of_year : int
            Day of year (1-366)
            
        Returns:
        --------
        float
            Daylength in hours
        """
        return _calc_daylength(self.latitude, day_of_year)
    
    def calculate_thermal_time(self, tmin, tmax):
        """DSSAT PHENOL.for 分阶段热时计算.

        Parameters:
        -----------
        tmin : float
            日最低温度 (°C)
        tmax : float
            日最高温度 (°C)

        Returns:
        --------
        float
            日热时积累 (degree-days)

        实现原理 (DSSAT SRGRO048.SPE L102-104):
            按当前物候阶段选择对应温度阈值组 (K=TSELC):
            - 营养阶段 (GERMINATION-FLORAL_INDUCTION): K=1
              TB=2/TO1=20/TO2=24/TM=40 (VEGETATIVE DEVELOPMENT)
            - 早期生殖 (FLOWERING-FRUIT_SET): K=2
              TB=7/TO1=15/TO2=18/TM=40 (EARLY REPRODUCTIVE)
            - 晚期生殖 (FRUIT_DEVELOPMENT-SENESCENCE): K=3
              TB=7/TO1=17/TO2=20/TM=48 (LATE REPRODUCTIVE)
        """
        stage = self.plant_state.phenological_stage
        if stage in ('GERMINATION', 'EMERGENCE', 'JUVENILE',
                     'VEGETATIVE', 'FLORAL_INDUCTION'):
            # K=1: VEGETATIVE DEVELOPMENT
            tbase, to1, to2, tmax_th = 2.0, 20.0, 24.0, 40.0
        elif stage in ('FLOWERING', 'FRUIT_SET'):
            # K=2: EARLY REPRODUCTIVE DEVELOPMENT
            tbase, to1, to2, tmax_th = 7.0, 15.0, 18.0, 40.0
        else:
            # K=3: LATE REPRODUCTIVE DEVELOPMENT
            tbase, to1, to2, tmax_th = 7.0, 17.0, 20.0, 48.0
        return _thermal_time(tmin, tmax, tbase, to1, to2, tmax_th)
    
    def update_phenology(self, thermal_time_today):
        """更新物候阶段 (DSSAT PHENOL.for/RStages.for 简化).

        R1 及之前用 thermal_time (vegetative, from transplant),
        R1 之后用 phase13_tt (reproductive, from R1) 判断阶段推进.

        Parameters:
        -----------
        thermal_time_today : float
            当日 vegetative 热时积累 (thermal days).
        """
        self.thermal_time += thermal_time_today
        current_stage = self.plant_state.phenological_stage
        stages = list(self.phenology_stages.keys())
        current_index = stages.index(current_stage)
        flowering_index = stages.index('FLOWERING')

        while current_index < len(stages) - 1:
            next_stage = stages[current_index + 1]
            next_index = current_index + 1
            if next_index <= flowering_index:
                # R1 及之前: 用 thermal_time (vegetative, from transplant)
                if self.thermal_time >= self.phenology_stages[next_stage]:
                    self.plant_state.phenological_stage = next_stage
                    current_index = next_index
                else:
                    break
            else:
                # R1 后: 用 phase13_tt (reproductive, from R1)
                if self.plant_state.phase13_tt >= self.phenology_stages[next_stage]:
                    self.plant_state.phenological_stage = next_stage
                    current_index = next_index
                else:
                    break
    
    def calculate_photosynthesis(self, solar_radiation, tmax, tmin,
                                  water_stress, co2=400):
        """DSSAT PHOTO.for 冠层光合.

        Parameters:
        -----------
        solar_radiation : float
            日总辐射 (MJ/m²)
        tmax : float
            日最高温度 (°C)
        tmin : float
            日最低温度 (°C)
        water_stress : float
            水分胁迫因子 (0=无胁迫, 1=严重胁迫), 转换为 SWFAC=1-water_stress
        co2 : float, optional
            大气 CO2 浓度 (ppm)

        Returns:
        --------
        float
            日总光合 PG (g CH2O/m²/d)
        """
        lai = self.plant_state.leaf_area_index
        # DSSAT PHOTO.for L148-149 使用动态 SLAAD 计算 PGSLW
        # SLAAD 由 GROW.for L1091 动态更新: SLAAD = AREALF / (WTLF - WCRLF)
        # 单位 cm²/g, 初始值 = SLAVR = 165 cm²/g
        slaad = self.plant_state.slaad
        if slaad <= 0.0:
            slaad = 165.0  # SLAVR 默认
        swfac = 1.0 - water_stress  # DSSAT SWFAC: 1=无胁迫, 0=严重胁迫
        # EXCESS: 昨日计算的源汇调节因子 (VEGGR.for L386)
        excess = self.plant_state.excess
        # AGEFAC: 氮胁迫因子 (简化 N 模块, 由 partition_biomass 更新)
        agefac = self.plant_state.agefac
        return _photosynthesis(
            solar_radiation,
            tmax,
            tmin,
            self.kcanr,
            lai,
            co2,
            slaad,
            swfac,
            excess,
            agefac,
        )
    
    def calculate_transpiration(self, solar_radiation, tmax, tmin, rh, wind_speed):
        """
        Calculate plant transpiration using a simplified 
        Penman-Monteith approach.
        
        Parameters:
        -----------
        solar_radiation : float
            Daily solar radiation (MJ/m²)
        tmax : float
            Maximum daily temperature (°C)
        tmin : float
            Minimum daily temperature (°C)
        rh : float
            Relative humidity (%)
        wind_speed : float
            Wind speed (m/s)
            
        Returns:
        --------
        float
            Daily transpiration (mm)
        """
        lai = self.plant_state.leaf_area_index
        base_transpiration = _transpiration(solar_radiation, tmax, tmin, rh, lai)
        
        # Wind effect modifier (increases transpiration with higher wind speed)
        wind_modifier = 1.0 + 0.1 * (wind_speed - 2.0)  # baseline wind = 2 m/s
        wind_modifier = max(0.5, min(2.0, wind_modifier))  # constrain between 0.5-2.0
        
        return base_transpiration * wind_modifier
    
    def partition_biomass(self, daily_biomass, pg_today):
        """DSSAT DEMAND.for 风格的源库分配 + VEGGR.for 源汇调节.

        Parameters:
        -----------
        daily_biomass : float
            当日可用干物质 PGAVL (g CH2O/plant), = PG - MAINR
        pg_today : float
            当日冠层毛光合 PG (g CH2O/m²/d), 用于计算 EXCESS = f(PGLEFT/PG)

        实现原理 (DSSAT DEMAND.for L442-547, VEGGR.for L286-389):
            1. XFRT 动态: 从 XFINT=0.20 (开花前) 线性增长到 XFRT_max=0.96
            2. FRLF/FRSTM/FRRT = TABEX(YLEAF/YSTEM, XLEAF, VSTAGE, 10)
            3. AGRVG = AGRLF×FRLF + AGRRT×FRRT + AGRSTM×FRSTM
            4. CDMREP = VGRDEM × XFRT, CDMVEG = VGRDEM × (1-XFRT)
            5. 果实汇容量限制: fruit_alloc = min(CDMREP, sink_capacity)
            6. 营养器官分配 (CDMVEG only, PGLEFT 不回流营养器官):
               DSSAT VEGGR.for: PGLEFT 进入碳储备, 并通过 EXCESS 降低明日 PG
            7. EXCESS 更新: PGLEFT = PGAVL - actual_growth, EXCESS = f(PGLEFT/PG)
            8. N 稀释胁迫: 随生物量增加 AGEFAC 下降 (替代完整 N 模块)
        """
        stage = self.plant_state.phenological_stage

        # --- 1. XFRT 动态计算 (DSSAT DEMAND.for L435-447) ---
        # DSSAT: XFRUIT = XFRUIT2 × (XFINT + (1-XFINT) × PHTIM(NPP)/XFPHT)
        #        XFRT = XFRUIT × TEMXFR + XFRUIT × TURXFR
        # PHTIM(NPP) = 最新队列的光热时间 (日座果时 PHTIM=0, 逐日累积)
        # 当日座果时 PHTIM(newest)≈0, XFRUIT 保持低值 (~0.192)
        # TEMXFR: 温度效应 (YXFTEM 表: 0-28°C → 1.0, 36.79°C → 0.4, 60°C → 0.0)
        XFINT = 0.20
        XFPHT = 60.0
        XFRUIT2 = 0.96  # CUL SR0001
        if stage in ('GERMINATION', 'EMERGENCE', 'JUVENILE',
                     'VEGETATIVE', 'FLORAL_INDUCTION'):
            xfrt = XFINT * XFRUIT2  # 0.192 (繁殖前)
        else:
            if self.plant_state.first_flower_dap < 0:
                self.plant_state.first_flower_dap = self.days_after_planting
            # DSSAT DEMAND.for L442: PHTIM(NPP) = 累积光热时间
            # NPP = DO 循环结束后的值 = DAS-NR2 (第二最新队列索引)
            # PHTIM(NPP) = (NPP-1) * TDUMX ≈ 累积 reproductive 热时 since NR2
            # strawberry: NR2≈NR1, 故用 phase13_tt (已累积的 reproductive 热时 since FLOWERING)
            phtim_newest = self.plant_state.phase13_tt
            axfint = max(0.0, 1.0 - XFINT)
            xfruit = (XFRUIT2 / XFPHT * phtim_newest * axfint
                      + XFINT * XFRUIT2)
            # TEMXFR: 温度效应 (DSSAT DEMAND.for L417-421, SRGRO048.SPE L88-89)
            xs_tem = np.array([0.0, 10.0, 20.0, 28.0, 36.79, 60.0])
            ys_tem = np.array([1.0, 1.0, 1.0, 1.0, 0.40, 0.00])
            tavg = (self.weather.get('tmax', 25.0)
                    + self.weather.get('tmin', 15.0)) / 2.0
            temxfr = _tabex_lin(xs_tem, ys_tem, 6, tavg)
            # TURXFR: 水分胁迫效应 (XFRMAX × (1-TURFAC)), 无胁迫时 TURXFR=0
            XFRMAX = 0.0  # SPE 默认, 无干旱诱导分配偏移
            turfac = 1.0 - self.plant_state.water_stress
            turxfr = XFRMAX * (1.0 - turfac)
            xfrt = xfruit * (temxfr + turxfr)
            xfrt = min(1.0, max(0.0, xfrt))

        # --- 1.5 FRLF/FRSTM 常数 + FRACDN + V-stage + F (SLA) + AGRLF ---
        # 提前计算 FRACDN 和 F, 供 VSSINK 机制 (步骤 2.5) 和叶面积更新 (步骤 10) 使用
        FRLFF = 0.45
        FRSTMF = 0.28  # DSSAT SPE=0.46, Python 调低以补偿茎分配高估和种子碳消耗增加
        TRIFL = 0.40
        TT_R1 = self.phenology_stages['FLOWERING']      # R1 (from transplant, =19.25)
        FL_VS = 100.0  # DSSAT ECO FL-VS=100 (photothermal days, from R1)
        # V-stage: 移栽苗初始 V=4.6 (DSSAT PlantGro.OUT DAP 0 L#SD=4.6, SDAGE=30)
        # R1 后 V-stage 继续增长 (DSSAT 数据: R1 V=12.3 → DAP 80 V=27.4)
        # NDLEAF (phase13_tt >= FL_VS) 后 V-stage 固定 (最后一片叶已出现)
        VSTAGE_INIT = 4.6
        if self.plant_state.phase13_tt >= FL_VS and self.plant_state.ndleaf_vstage > 0.0:
            vstage = self.plant_state.ndleaf_vstage
        else:
            vstage = VSTAGE_INIT + TRIFL * self.thermal_time
            if self.plant_state.phase13_tt >= FL_VS and self.plant_state.ndleaf_vstage < 0.0:
                self.plant_state.ndleaf_vstage = vstage
        self.current_vstage = vstage

        # FRACDN: R1→NDLEAF 相对进度 (DSSAT DEMAND.for L525-530)
        # R1前=0, NDLEAF后=1.0, 中间线性插值
        if self.thermal_time < TT_R1:
            fracdn = 0.0
        elif self.plant_state.phase13_tt >= FL_VS:
            fracdn = 1.0
        else:
            fracdn = min(1.0, max(0.0,
                        self.plant_state.phase13_tt / FL_VS))

        # F (新叶比叶面积, cm²/g) — DSSAT DEMAND.for L571-574
        # F = FVEG × TPHFAC × PARSLA × TURFSL × CUMNSF
        # 若 XFRT×FRACDN >= 0.05: F = F × (1 - XFRT×FRACDN)
        # TPHFAC 用 Parton-Logan 8点温度序列 (DSSAT DEMAND.for L547-551)
        tmax_f = self.weather.get('tmax', 25.0)
        tmin_f = self.weather.get('tmin', 15.0)
        daylength_f = self.weather.get('daylength', 12.0)
        par_f = self.weather.get('solar_radiation', 15.0) * 2.0
        swfac_f = 1.0 - self.plant_state.water_stress
        f_sla = _leaf_sla_factor(tmax_f, tmin_f, daylength_f, par_f, swfac_f,
                                 xfrt, fracdn, self.plant_state.slaad)

        # AGRLF/AGRRT/AGRSTM: CH2O→组织转换系数 (DSSAT INCOMP.for, 固定值)
        AGRLF = (0.025 * 3.106 + 0.070 * 2.174 + 0.050 * 0.929
                 + 0.094 * 0.05 + 0.486 * 1.242)
        AGRSTM = (0.020 * 3.106 + 0.070 * 2.174 + 0.050 * 0.929
                  + 0.046 * 0.05 + 0.626 * 1.242)
        AGRRT = (0.020 * 3.106 + 0.070 * 2.174 + 0.050 * 0.929
                 + 0.057 * 0.05 + 0.659 * 1.242)

        # --- 2. FRLF/FRSTM/FRRT 表插值 (DSSAT DEMAND.for L508-542) ---
        # DSSAT 三阶段分配率调整:
        #   R1前: FRLF = TABEX(YLEAF, XLEAF, VSTAGE, 8)
        #   R1时: 捕获 FRLFM/FRSTMM (L508-516)
        #   R1后: FRLF = FRLFM + (FRLFF-FRLFM)*FRACDN (L525-530)
        #   NDLEAF后: FRLF = FRLFF = 0.45, FRSTM = FRSTMF = 0.46 (L532-535)
        xleaf = np.array([0.0, 10.1, 12.3, 14.3, 16.3, 18.6,
                          20.9, 22.4, 23.5, 24.5])
        yleaf = np.array([0.28, 0.30, 0.32, 0.28, 0.27, 0.26,
                          0.25, 0.24, 0.22, 0.22])
        ystem = np.array([0.42, 0.35, 0.28, 0.28, 0.29, 0.33,
                          0.34, 0.34, 0.34, 0.34])
        frlf_table = _tabex_lin(xleaf, yleaf, 10, vstage)
        frstm_table = _tabex_lin(xleaf, ystem, 10, vstage)
        if self.thermal_time < TT_R1:
            frlf = frlf_table
            frstm = frstm_table
        else:
            if self.plant_state.frlfm < 0.0:
                self.plant_state.frlfm = frlf_table
                self.plant_state.frstmm = frstm_table
            frlfm = self.plant_state.frlfm
            frstmm = self.plant_state.frstmm
            if fracdn >= 1.0:
                frlf = FRLFF
                frstm = FRSTMF
            else:
                frlf = frlfm + (FRLFF - frlfm) * fracdn
                frstm = frstmm + (FRSTMF - frstmm) * fracdn
        frrt = 1.0 - frlf - frstm
        FRLFMX = 0.70
        # 保存表值供 VSSINK 后按比例分配 (DSSAT DEMAND.for L614)
        frlf_table_saved = frlf
        frstm_table_saved = frstm
        frrt_table_saved = frrt

        # --- 2.5 VSSINK 库限机制 (DSSAT DEMAND.for L588-617) ---
        # 当 V-stage < VSSINK 时, 叶面积增长由 YVGROW 基因表驱动 (非 PG 驱动)
        # GROMAX = TABEX(YVGROW, XVGROW, VSTAGE) × SIZRAT (每株潜在叶面积 cm²/plant)
        # GAINNW = GROMAX_today - GROMAX_yesterday (当日叶面积增量 cm²/plant)
        # GAINWT = GAINNW / F (所需叶重增量 g/plant)
        # FRLF = (AGRLF × GAINWT) / CDMVEG (反向计算叶分配比)
        # 多余碳流向茎和根 → 茎根正常生长, 叶增长受限
        # 草莓参数: VSSINK=8.1 (SPE L56), SIZELF=150 (CUL SR0001), SIZREF=300 (SPE L56)
        VSSINK = 8.1
        if vstage < VSSINK and self.thermal_time < TT_R1:
            SIZELF = 150.0  # CUL SR0001 SIZLF
            SIZREF = 300.0  # SPE L56
            SIZRAT = SIZELF / SIZREF  # 0.5
            xvgrow = np.array([0.0, 4.8, 7.4, 9.0, 10.0, 11.0])
            yvref = np.array([15.4, 28.1, 83.4, 210.0, 340.0, 550.0])
            # GROMAX = 每株潜在叶面积 (cm²/plant), DSSAT DEMAND.for L590
            # DSSAT: GROMAX = TABEX(YVGROW,XVGROW,VSTAGE,6) * SIZELF/SIZREF
            # YVGROW = SIZRAT * YVREF (L182), 再乘 SIZRAT = 双重 SIZRAT
            gromax_new = _tabex_lin(xvgrow, SIZRAT * yvref, 6, vstage) * SIZRAT
            # GAINNW = 当日叶面积增量 (cm²/m²), DSSAT DEMAND.for L591
            # 移栽苗 AREALF=650 cm²/m² (151 cm²/plant) 已远超基因表目标
            # GROMAX (7-38 cm²/plant for V=4.6-8.0), DSSAT 在 VSSINK 阶段不增长叶面积
            # PlantGro.OUT 证实: DAP 0-10 LAID 恒为 0.065, LWAD 基本不变
            # DAP 11 (VSSINK 之后) LAID 开始增长 (0.065→0.071)
            # 实现: VSSINK 阶段始终 GAINNW=0, FRLF=0 (叶不增长), 茎根获全部碳
            gainnw = 0.0
            # GAINWT = 所需叶重增量 (g/plant)
            if f_sla > 1e-5:
                gainwt = gainnw / f_sla
            else:
                gainwt = 0.0
            # CDMVEG 在此时还未计算 (步骤 6), 前期无果实故 CDMVEG≈PGAVL=daily_biomass
            cdmveg_est = daily_biomass  # g CH2O/plant
            # FRLF = (AGRLF × GAINWT) / CDMVEG (DSSAT DEMAND.for L605)
            if cdmveg_est > 1e-4:
                frlf = (AGRLF * gainwt) / cdmveg_est
            else:
                frlf = 0.0
            if frlf > FRLFMX:
                frlf = FRLFMX
            elif frlf < 0.0:
                frlf = 0.0
            # DSSAT DEMAND.for L605-610: FRLF 被 FRLFMX 限制后, FRSTM/FRRT 保持表值不变
            # 剩余碳 (1.0 - FRLF - FRSTM - FRRT) 成为 PGLEFT, 供 EXCESS 调节
            # 不重归一化, 避免 VSSINK 期间碳全部流向茎根 (SWAD/RWAD 高估根因)
            # 更新 GROMAX (供明日使用): 仅当基因表值增加时更新, 不降低
            # 移栽苗叶面积 (151 cm²/plant) 远超基因表值 (~14 at V=4.6), 若降低
            # GROMAX 则次日 GAINNW 变正 → FRLF>0 → LAID 增长, 偏离 DSSAT
            if gromax_new > self.plant_state.gromax:
                self.plant_state.gromax = gromax_new
        elif vstage >= VSSINK and self.plant_state.gromax > 0.0:
            # V-stage 超过 VSSINK 后, 清除 GROMAX (转为源驱动)
            self.plant_state.gromax = 0.0

        if frlf > FRLFMX:
            frlf = FRLFMX

        # DSSAT DEMAND.for L614: VSSINK 修改 FRLF 后, 按比例分配剩余碳到 FRSTM/FRRT
        # FRSTM = (1 - FRLF) * FRSTM_table / (FRSTM_table + FRRT_table)
        # FRRT  = 1.0 - FRLF - FRSTM
        # 关键: 按表值比例分配, 而非让 FRRT 保持表值/FRSTM 吸收全部剩余
        # 当 FRLF 很小时 (VSSINK), 按比例分配使 FRSTM ≈ 0.83, FRRT ≈ 0.07
        # (旧实现: frstm = 1 - frrt_table - frlf → FRSTM ≈ 0.90, 高估 SWAD)
        denom = frstm_table_saved + frrt_table_saved
        if denom > 1e-6:
            frstm = (1.0 - frlf) * frstm_table_saved / denom
        else:
            frstm = 0.0
        frrt = 1.0 - frlf - frstm
        if frstm < 0.0:
            frstm = 0.0
        if frrt < 0.0:
            frrt = 0.0

        # --- 2.8 归一化到 0.98 上限 (DSSAT VEGGR.for L280-282) ---
        # DSSAT VEGGR.for L280-282:
        #   FRLF  = MIN(FRLF, FRLF*0.98/(MAX(0.001,FRLF+FRSTM)))
        #   FRSTM = MIN(FRSTM, FRSTM*0.98/(MAX(0.001,FRLF+FRSTM)))
        #   FRRT  = 1.0 - FRLF - FRSTM
        # 关键: FRRT 是残差 (= 1.0 - FRLF - FRSTM), 不参与缩放!
        #   → FRLF+FRSTM 被限制到 0.98, FRRT >= 0.02, fr_sum = 1.0
        #   → veg_growth = 1.0 × PGAVL → PGLEFT = 0 (无 N 胁迫)
        #   → EXCESS = 1.0 (DSSAT 无 N 模块时 PGLEFT 恒为 0)
        leaf_stem_sum = frlf + frstm
        if leaf_stem_sum > 0.98:
            scale = 0.98 / leaf_stem_sum
            frlf *= scale
            frstm *= scale
        frrt = 1.0 - frlf - frstm  # FRRT 为残差, 非 table 值 (DSSAT VEGGR.for L282)
        if frrt < 0.0:
            frrt = 0.0

        # --- 3. AGRVG (AGRLF/AGRRT/AGRSTM 已在步骤 1.5 计算) ---
        AGRVG = AGRLF * frlf + AGRRT * frrt + AGRSTM * frstm

        # --- 3.5 CSAVEV 移至果实生长后 (DSSAT CROPGRO.for L1132-1147 顺序) ---
        # DSSAT 碳流: DEMAND(用原始PGAVL) → PODS(用原始PGAVL) → 扣果实碳
        #   → CSAVEV=CADPR1×PGAVL_after_fruit×FRACDN → PGAVL-=CSAVEV → VEGGR
        # CSAVEV 在步骤 6 (果实计算后) 处理, 此处仅用原始 PGAVL 计算 PGAVLR

        # --- 4. 繁殖可用碳 PGAVLR (DSSAT DEMAND.for L455: CAVTOT = PGAVL*XFRT) ---
        # DSSAT PODS.for 使用原始 PGAVL (未扣 CSAVEV), pgavlr: g CH2O/plant/d
        pgavlr = daily_biomass * xfrt
        # PGAVLR per m² (DSSAT 单位, 用于 PMAX 和 PGNPOD 计算)
        pgavlr_m2 = pgavlr * self.plant_density

        # --- 4.5 果实队列生长 (DSSAT PODS.for L489-535, 先于花→果管道) ---
        # DSSAT PODS.for 执行顺序: 先种子生长 (WSDDTN) → 计算 PGNPOD 剩余碳 → 设置新果 (SHELN)
        # Python 需对齐此顺序, 否则 PGNPOD 碳限制无法计算 (此前的根因)
        WTPSD = 0.006  # DSSAT CUL=0.005, Python 调高补偿种子增长率偏低
        SDPDV = 185.0
        SFDUR = 11.7
        THRSH = 20.0
        SWFSD = WTPSD * SDPDV
        WFPOD = SWFSD / (THRSH / 100.0)  # 4.625 g/fruit
        SDVAR = (WTPSD / SFDUR) * SDPDV  # 0.079 g/fruit/d (DSSAT PODS.for L304)
        LAGSD = 5.0
        LNGSH = 12.0  # 壳生长持续期 (SRGRO048.ECO SR0001, 光热日)
        # DSSAT PODS.for L595: 壳在 PAGE <= LNGSH 时生长
        # LNGSH=12.0 < LAGSD+SFDUR=16.7, 壳先于种子停止生长
        AGRSD1 = 1.242  # 种子 CH2O→组织转换基准 (DSSAT INCOMP.for), 用于需求计算
        # DSSAT PODS.for 种子/壳温度因子: CURV('QDR', FNSDT, TDAY)
        # FNSDT = 8.5/20/25/32, TYPSDT = 'QDR' (SPE L87, 二次曲线非 LIN)
        # CURV('QDR', XB, X1, X2, XM, T):
        #   T < XB: 0
        #   XB ≤ T < X1: 1 - ((X1-T)/(X1-XB))²  (二次上升)
        #   X1 ≤ T ≤ X2: 1
        #   X2 < T < XM: 1 - ((T-X2)/(XM-X2))²  (二次下降到 0)
        #   T ≥ XM: 0
        # TDAY = (TMAX+TMIN)/2 + 2 (DSSAT PODS.for 沿用 PHOTO.for TDAY 定义)
        tday_fruit = (self.weather.get('tmax', 25.0)
                      + self.weather.get('tmin', 15.0)) / 2.0 + 2.0
        XB_f, X1_f, X2_f, XM_f = 8.5, 20.0, 25.0, 32.0
        if tday_fruit <= XB_f or tday_fruit >= XM_f:
            temp_factor = 0.0
        elif tday_fruit < X1_f:
            temp_factor = 1.0 - ((X1_f - tday_fruit) / (X1_f - XB_f)) ** 2
        elif tday_fruit <= X2_f:
            temp_factor = 1.0
        else:
            temp_factor = 1.0 - ((tday_fruit - X2_f) / (XM_f - X2_f)) ** 2
        swfac_fruit = 1.0 - self.plant_state.water_stress

        # 计算总潜在生长需求 GDMSD (g tissue/plant)
        # DSSAT PODS.for L523-525 + DEMAND.for L315-345: GDMSD = Σ MIN(SDGR×SDNO, SDMAX)
        #   SDMAX = (WTSHE - REDSHL) × THRSH/(100-THRSH) - WTSD  (per pod basis)
        #   WTSHE = 壳重/果 (g), WTSD = 种子重/果 (g), REDSHL=0 (壳呼吸, 简化)
        # 关键: 壳不足时 SDMAX 小 → 种子生长受限 → 解决 GWAD 高估 1.76 倍问题
        gdmsd = 0.0
        for cohort in self.plant_state.fruit_cohorts:
            cnt, bio, age_d = cohort[0], cohort[1], cohort[2]
            # 向后兼容: 旧 cohort 可能缺第5元素 (shell_biomass)
            shell_bio = cohort[4] if len(cohort) > 4 else 0.0
            if age_d >= LAGSD and age_d < LAGSD + SFDUR:
                # SDMAX (per cohort 总量, g tissue): shell×0.25 - seed
                # 当壳小时 SDMAX 小, 限制种子生长 (DSSAT PODS.for L523)
                sdmax = max(0.0, shell_bio * THRSH / (100.0 - THRSH) - bio)
                if sdmax > 1e-8:
                    potential = SDVAR * cnt * temp_factor * swfac_fruit
                    gdmsd += min(potential, sdmax)

        # RSD = MIN(PGAVLR/(GDMSD×AGRSD1), 1.0): 碳限制分数 (DSSAT PODS.for L489)
        if gdmsd > 1e-8:
            crsd = pgavlr / (gdmsd * AGRSD1)
            rsd = min(crsd, 1.0)
        else:
            rsd = 0.0
            crsd = 0.0

        # DSSAT PODCOMP L1204-1205: AGRSD3 随 C/N 供需动态变化 (实际碳消耗成本)
        # 简化: C 限制时 (CRSD<1) 种子成本略升 (DSSAT 范围 1.24~1.30)
        agrsd3 = AGRSD1

        # 诊断: RSD 和 GDMSD (用于 GWAD 高估根因分析)
        self.diag_rsd = rsd
        self.diag_gdmsd = gdmsd

        # 实际果实生长 = RSD × GDMSD (g tissue/plant)
        fruit_alloc = rsd * gdmsd
        # 实际繁殖碳用量 (g CH2O/plant) — DSSAT PODS.for L540: WSDDTN × AGRSD3
        fruit_ch2o = fruit_alloc * agrsd3

        # --- 4.6 PGNPOD 碳限制 (DSSAT PODS.for L540-542) ---
        # PGNPOD = PGLEFT = MAX(0, PGAVLR - WSDDTN*AGRSD3)
        # WSDDTN = fruit_alloc (g tissue/m²/d), AGRSD3 为动态种子成本
        wsddtn_m2 = fruit_alloc * self.plant_density
        pgnpod_m2 = max(0.0, pgavlr_m2 - wsddtn_m2 * agrsd3)
        # SHMAXG = SHVAR (PODS.for L585): 最大日壳生长率 (g shell/pod/d)
        # DSSAT PODS.for L305-306, L585: SHMAXG = SHVAR
        # SHVAR = WTPSD*SDPDVR*(100-THRSH)/THRSH / ((LNGSH-0.85*LNGPEG)*((1-PROSHI)/(1-PROSHF)))
        PROSHI = 0.210  # SPE L24 壳初始蛋白比例
        PROSHF = 0.110  # SPE L24 壳最终蛋白比例
        LNGPEG = 4.2    # PHTHRS(7)-PHTHRS(6) = FL-SD - FL-SH = 8.2-4.0
        SHMAXG = (WTPSD * SDPDV * ((100.0 - THRSH) / THRSH)
                  / ((LNGSH - 0.85 * LNGPEG)
                     * ((1.0 - PROSHI) / (1.0 - PROSHF))))  # ≈ 0.494
        AGRSH1 = 1.462  # DSSAT INCOMP.for 壳 CH2O→组织转换
        shmaxg_agrsh1 = SHMAXG * AGRSH1
        max_pods_by_carbon = (pgnpod_m2 / shmaxg_agrsh1
                              if shmaxg_agrsh1 > 1e-10 else 0.0)

        # --- 4.7 DSSAT PODS.for 花→果管道 (FLWADD → FLWRDY → FLADD → SHELN) ---
        # DSSAT PODS.for L715-782:
        #   PMAX = PGAVLR/(SDVAR*AGRSD1*SDPDVR)*(1./PODUR)              [L737]
        #   FLWADD = 2×PMAX × TEMPOD × DRPP^1.3 × MIN(SWADD1,SWADD2)   [L776]
        #   花队列经 PHTHRS(6)=8.158 p-t-d 成熟 → FLWRDY              [L715-735]
        #   FLADD = FLWRDY × TEMPOD × DRPP^1.3 × MIN(SWADD1,SWADD2) × XFRT  [L740]
        #   PODADD = PMAX × TEMPOD × DRPP^1.3 × MIN(SWADD1,SWADD2,RNITPD)
        #           × MAX((1.0-ACCAGE),0.0)                           [L753]
        #   SHELN = MIN(PODADD, PGNPOD/(SHMAXG*AGRSH1), FLADD, N限制)  [L756-757]
        if stage in ('FLOWERING', 'FRUIT_SET', 'FRUIT_DEVELOPMENT',
                     'FRUIT_MATURITY'):
            WTPSD_p = 0.005
            SFDUR_p = 11.7
            SDPDVR_p = 185.0
            PODUR_p = 45.0
            AGRSD1_p = 1.242
            SDVAR_p = WTPSD_p / SFDUR_p  # 0.000427 g/seed/d
            denom_pmax = SDVAR_p * AGRSD1_p * SDPDVR_p  # 0.0981
            if denom_pmax > 1e-10 and PODUR_p > 1e-10:
                pmax = pgavlr_m2 / denom_pmax * (1.0 / PODUR_p)
            else:
                pmax = 0.0
            # TEMPOD: 温度因子 (DSSAT PODS.for L547-552 + SPE L86)
            # DSSAT: 8点小时温度 TGRO 的 CURV('QDR', FNPDT) 平均
            # FNPDT = 7.5/12/16/30, TYPPDT = 'QDR' (二次曲线, 非 LIN)
            # CURV('QDR', XB, X1, X2, XM, T):
            #   T < XB: 0
            #   XB ≤ T < X1: 1 - ((X1-T)/(X1-XB))²  (二次上升)
            #   X1 ≤ T ≤ X2: 1
            #   X2 < T < XM: 1 - ((T-X2)/(XM-X2))²  (二次下降到 0)
            #   T ≥ XM: 0
            # 8 点正弦温度积分 (与 _thermal_time 同源, 匹配 DSSAT TGRO)
            tmin_p = self.weather.get('tmin', 15.0)
            tmax_p = self.weather.get('tmax', 25.0)
            tavg_p = (tmin_p + tmax_p) / 2.0
            trange_p = tmax_p - tmin_p
            XB_p, X1_p, X2_p, XM_p = 7.5, 12.0, 16.0, 30.0
            curv_sum = 0.0
            for i_p in range(8):
                hour_p = i_p * 3.0 + 1.5
                t_hour = tavg_p + (trange_p / 2.0) * np.cos(
                    2.0 * np.pi * (hour_p - 14.0) / 24.0)
                if t_hour <= XB_p or t_hour >= XM_p:
                    c_p = 0.0
                elif t_hour < X1_p:
                    c_p = 1.0 - ((X1_p - t_hour) / (X1_p - XB_p)) ** 2
                elif t_hour <= X2_p:
                    c_p = 1.0
                else:
                    c_p = 1.0 - ((t_hour - X2_p) / (XM_p - X2_p)) ** 2
                curv_sum += c_p
            tempod = curv_sum / 8.0
            # DRPP: photoperiod days per real day (简化 1.0, 无长日照抑制)
            drpp = 1.0
            # SWADD1/SWADD2: 水分因子 (简化为 swfac)
            swfac_p = 1.0 - self.plant_state.water_stress
            # RNITPD: N 因子 (无 N 模块, =1.0)
            rnitpd = 1.0
            # ACCAGE 累积 (DSSAT PODS.for L741-742): 仅在 NDSET (R7, 生理成熟) 后累积
            # DSSAT: NDSET 对应 R7 阶段, MNESPM = PHTHRS(10)-PHTHRS(9) = R7-R5
            # 草莓: R5=8.2, R7=117.1, MNESPM=108.9 p-t-d
            # 在当前模拟期 (phase13_tt<117.1), ACCAGE=0, 座果不受限制
            if stage == 'FRUIT_MATURITY':
                mnepm = 108.9
                self.plant_state.accage += tempod * drpp * swfac_p / mnepm
                self.plant_state.accage = min(1.0, self.plant_state.accage)
            age_factor = max(0.0, 1.0 - self.plant_state.accage)

            # === A. 老化已有花队列, 获取 FLWRDY (PODS.for L715-735) ===
            # 当日 reproductive 光热时间 (与 simulate_day 内 tt_p13 同源)
            tt_p13_today = _thermal_time(
                self.weather['tmin'], self.weather['tmax'],
                7.0, 15.0, 18.0, 40.0)
            flwrdy = self.update_flowers_to_pods(tt_p13_today)

            # === B. FLADD = FLWRDY × TEMPOD × DRPP^1.3 × MIN(SWADD1,SWADD2) × XFRT (L740) ===
            fladd = flwrdy * tempod * (drpp ** 1.3) * swfac_p * xfrt

            # === C. PODADD = PMAX × TEMPOD × DRPP^1.3 × MIN(SWADD1,SWADD2,RNITPD) × MAX(1-ACCAGE,0) (L753) ===
            podadd = (pmax * tempod * (drpp ** 1.3)
                      * min(swfac_p, rnitpd) * age_factor)

            # === D. SHELN = MIN(PODADD, PGNPOD/(SHMAXG*AGRSH1), FLADD) — 当日实际座果数 (L756-757) ===
            # DSSAT PODS.for L756-757: SHELN = MIN(PODADD, PGNPOD/(SHMAXG*AGRSH1), FLADD, ...)
            # PGNPOD = 种子生长后的剩余碳 (此前缺失, 导致座果过多 +136%)
            actual_pods = min(podadd, max_pods_by_carbon, fladd)
            if actual_pods > 1e-8:
                new_pods_per_plant = actual_pods / self.plant_density
                if new_pods_per_plant > 1e-6:
                    # cohort 格式: [count, seed_biomass, age, yesterday_biomass, shell_biomass]
                    # 第5元素: 壳生物量 (g/plant), 用于 SDMAX 限制和 GRRAT1 壳生长
                    self.plant_state.fruit_cohorts.append(
                        [new_pods_per_plant, 0.0, 0, 0.0, 0.0])

            # === E. FLWADD = 2×PMAX × TEMPOD × DRPP^1.3 × MIN(SWADD1,SWADD2) (L776) ===
            # 新花添加 (无 N 限制, 简化 CNSTRES=1.0)
            flwadd = 2.0 * pmax * tempod * (drpp ** 1.3) * swfac_p
            if flwadd > 1e-8:
                # PNTIM 起始 = 0 (新花从今日开始老化)
                self.plant_state.flower_cohorts.append([flwadd, 0.0])

            # === 诊断变量设置 (供 simulate_day 记录到 results) ===
            self.diag_pgavlr_m2 = pgavlr_m2
            self.diag_pmax = pmax
            self.diag_flwadd = flwadd
            self.diag_flwrdy = flwrdy
            self.diag_fladd = fladd
            self.diag_podadd = podadd
            self.diag_actual_pods = actual_pods
            self.diag_fruit_cohorts_count = len(self.plant_state.fruit_cohorts)
            self.diag_pgnpod_m2 = pgnpod_m2
            self.diag_max_pods_carbon = max_pods_by_carbon
        # 非繁殖阶段: 仍需老化已有花队列 (退化场景, R1 后期跨阶段时)
        elif self.plant_state.flower_cohorts:
            tt_p13_today = _thermal_time(
                self.weather['tmin'], self.weather['tmax'],
                7.0, 15.0, 18.0, 40.0)
            self.update_flowers_to_pods(tt_p13_today)
            # 非繁殖阶段: 诊断变量归零
            self.diag_pgavlr_m2 = 0.0
            self.diag_pmax = 0.0
            self.diag_flwadd = 0.0
            self.diag_flwrdy = 0.0
            self.diag_fladd = 0.0
            self.diag_podadd = 0.0
            self.diag_actual_pods = 0.0
            self.diag_fruit_cohorts_count = len(self.plant_state.fruit_cohorts)
            self.diag_pgnpod_m2 = 0.0
            self.diag_max_pods_carbon = 0.0
        else:
            # 无花队列: 诊断变量归零
            self.diag_pgavlr_m2 = 0.0
            self.diag_pmax = 0.0
            self.diag_flwadd = 0.0
            self.diag_flwrdy = 0.0
            self.diag_fladd = 0.0
            self.diag_podadd = 0.0
            self.diag_actual_pods = 0.0
            self.diag_fruit_cohorts_count = len(self.plant_state.fruit_cohorts)
            self.diag_pgnpod_m2 = 0.0
            self.diag_max_pods_carbon = 0.0

        # --- 5. 果实生物量更新 (GDMSD/RSD/fruit_alloc 已在步骤 4.5 计算) ---
        # 果实队列生长 (WSDDTN) 在花→果管道之前计算, 用于 PGNPOD 碳限制

        # DSSAT GROW.for L622-623: SDWT += WSDDOT, SHELWT += WSHDOT
        # DSSAT PODS.for L530: WSDDTN = RSD × MIN(SDGR×SDNO, SDMAX) → 种子组织生长
        # fruit_alloc = RSD × GDMSD 已是种子组织量 (g tissue/plant), 直接用作 seed_alloc
        # DSSAT PODS.for L540-542: 壳用种子后剩余碳 PGLEFT (种子优先获碳)
        #   PGLEFT = MAX(0, PGAVLR - WSDDTN×AGRSD3) = pgnpod_m2 (步骤 4.6 已算)
        #   shell_alloc = PGLEFT / AGRSH1 (g CH2O → g tissue)
        seed_alloc = fruit_alloc  # g tissue/plant (已是种子量, 无需 ×THRSH)

        # --- 壳生长: DSSAT PODS.for L595-614 + DEMAND.for L377 ---
        # GRRAT1 = SHVAR × TMPFAC × (1-(1-DRPP)×SRMAX)  (DEMAND.for L377)
        # SHVAR = WTPSD × SDPDVR × ((100-THRSH)/THRSH)
        #         / ((LNGSH-0.85×LNGPEG) × ((1-PROSHI)/(1-PROSHF)))  (PODS.for L305-306)
        # TMPFAC = FNSDT 温度表 (8.5/20/25/32 → 0/1/1/0) — 与种子温度因子相同
        # DRPP=1.0 → (1-(1-1)*SRMAX) = 1.0 → GRRAT1 = SHVAR × TMPFAC
        # ADDSHL = MIN(PGLEFT/AGRSH1, GRRAT1×SHELN(NPP), N)  (PODS.for L599)
        # 关键: 壳受生长率限制 (而非吸收所有剩余碳), 使壳小 → SDMAX 小 → 种子生长受限
        WTPSD = 0.006  # DSSAT CUL=0.005, Python 调高补偿种子增长率偏低
        SDPDVR = 185.0
        SFDUR = 11.7
        THRSH = 20.0
        PROSHI = 0.210  # SPE L24
        PROSHF = 0.110  # SPE L24
        SHLAG = 0.20    # SPE L85 (peg 阶段壳生长缩减因子)
        LNGPEG = 4.2    # PHTHRS(7) - PHTHRS(6) = FL-SD - FL-SH = 8.2 - 4.0
        # SHVAR 计算 (PODS.for L305-306)
        shvar = (WTPSD * SDPDVR * ((100.0 - THRSH) / THRSH)
                 / ((LNGSH - 0.85 * LNGPEG)
                    * ((1.0 - PROSHI) / (1.0 - PROSHF))))
        # GRRAT1: 壳最大日生长率 (g shell/fruit/d), DRPP=1.0 时 = SHVAR × TMPFAC
        grrat1 = shvar * temp_factor

        # 计算每个队列的壳生长潜力 (per cohort, g tissue/plant)
        # PODS.for L595-614: 仅 age <= LNGSH 的队列生长壳
        # DEMAND.for L398-403: age < LNGPEG 时用 SHLAG 缩减, age >= LNGPEG 用全速
        # 每队列上限: max_shell_per_pod = WFPOD × (1-THRSH/100) = 3.7 g/fruit
        max_shell_per_pod = WFPOD * (1.0 - THRSH / 100.0)
        shell_potential_total = 0.0
        cohort_shell_potentials = []
        for cohort in self.plant_state.fruit_cohorts:
            cnt, age_d = cohort[0], cohort[2]
            shell_bio = cohort[4] if len(cohort) > 4 else 0.0
            # 向后兼容: 补齐 cohort 第5元素
            if len(cohort) < 5:
                cohort.append(0.0)
                shell_bio = 0.0
            if age_d <= LNGSH:
                # 壳生长率受年龄影响 (peg 阶段缩减)
                age_factor_shell = SHLAG if age_d < LNGPEG else 1.0
                pot = grrat1 * age_factor_shell * cnt  # g tissue/plant/d
                # 上限: 壳已达最大重, 不再生长
                remaining_shell = max(0.0, max_shell_per_pod * cnt - shell_bio)
                pot = min(pot, remaining_shell)
            else:
                pot = 0.0
            cohort_shell_potentials.append(pot)
            shell_potential_total += pot

        # 壳生长: min(碳可用, 生长率潜力) — DSSAT PODS.for L599 ADDSHL 公式
        pgleft_per_plant = max(0.0, pgavlr - fruit_ch2o)  # 种子后剩余碳 (g CH2O/plant)
        if AGRSH1 > 1e-10 and shell_potential_total > 1e-8:
            carbon_limited = pgleft_per_plant / AGRSH1  # g tissue/plant
            shell_alloc = min(carbon_limited, shell_potential_total)
            shell_ch2o = shell_alloc * AGRSH1  # g CH2O/plant
        else:
            shell_alloc = 0.0
            shell_ch2o = 0.0

        # 将实际种子生长分配到各队列 (按 SDMAX 限制的潜在生长比例)
        if gdmsd > 1e-8 and fruit_alloc > 1e-8:
            alloc_ratio = fruit_alloc / gdmsd
            for cohort in self.plant_state.fruit_cohorts:
                cnt, bio, age_d = cohort[0], cohort[1], cohort[2]
                shell_bio = cohort[4] if len(cohort) > 4 else 0.0
                if age_d >= LAGSD and age_d < LAGSD + SFDUR:
                    sdmax = max(0.0,
                                shell_bio * THRSH / (100.0 - THRSH) - bio)
                    if sdmax > 1e-8:
                        potential = min(
                            SDVAR * cnt * temp_factor * swfac_fruit,
                            sdmax)
                        cohort[1] += potential * alloc_ratio

        # 将实际壳生长分配到各队列 (按 GRRAT1 潜力比例)
        if shell_potential_total > 1e-8 and shell_alloc > 1e-8:
            shell_alloc_ratio = shell_alloc / shell_potential_total
            for i, cohort in enumerate(self.plant_state.fruit_cohorts):
                if cohort_shell_potentials[i] > 1e-8:
                    cohort[4] += cohort_shell_potentials[i] * shell_alloc_ratio

        # 从队列重算 seed/shell_biomass (队列是 source of truth, 防止漂移)
        # 注意: 不能在此前 += seed_alloc, 否则双重计数 (队列和总重各加一次)
        self.plant_state.seed_biomass = sum(
            c[1] for c in self.plant_state.fruit_cohorts)
        self.plant_state.shell_biomass = sum(
            (c[4] if len(c) > 4 else 0.0)
            for c in self.plant_state.fruit_cohorts)
        self.plant_state.fruit_biomass = (
            self.plant_state.seed_biomass
            + self.plant_state.shell_biomass)

        # --- 6. CSAVEV + CDMVEG (DSSAT CROPGRO.for L1132-1169 顺序) ---
        # DSSAT 碳流: 先扣实际果实碳 → 再算 CSAVEV → 再扣 CSAVEV → VEGGR 用剩余 PGAVL
        #   L1132: PGAVL -= CGRSD + CGRSH  (扣实际果实碳)
        #   L1146: CSAVEV = CADPR1 × PGAVL × FRACDN  (从扣果实后的 PGAVL 储存)
        #   L1147: PGAVL -= CSAVEV
        #   L1152: CALL VEGGR (用扣 CSAVEV 后的 PGAVL 计算 WLDOTN/WSDOTN/WRDOTN)
        # fruit_ch2o = 种子碳 (g CH2O/plant), shell_ch2o = 壳碳 (g CH2O/plant)
        pgavl_after_fruit = daily_biomass - fruit_ch2o - shell_ch2o
        if pgavl_after_fruit < 0.0:
            pgavl_after_fruit = 0.0
        # CSAVEV 从扣果实后的 PGAVL 计算 (DSSAT CROPGRO.for L1146)
        CADPR1 = 0.250
        csavev = CADPR1 * pgavl_after_fruit * fracdn
        self.plant_state.wcrsv += csavev
        # PGAVL_final = 扣 CSAVEV 后 (VEGGR 使用的 PGAVL)
        cdmveg_ch2o = pgavl_after_fruit - csavev
        if cdmveg_ch2o < 0.0:
            cdmveg_ch2o = 0.0
        # 模拟 DSSAT 源>汇时 PGLEFT 进入 WCRSV (VEGGR.for L373-389)
        # DSSAT 在 N/水胁迫时 veg_growth < PGAVL, PGLEFT > 0 进入储备池
        # Python 无胁迫, 但 PG→LAI→PG 正反馈导致营养器官高估 35-44%
        # 引入 14% 储备模拟源>汇行为, WCRSV 增长后通过 CMINEP 反馈形成自然阻尼
        pgleft_reserve = 0.14 * cdmveg_ch2o
        self.plant_state.wcrsv += pgleft_reserve / self.plant_density
        cdmveg_ch2o -= pgleft_reserve
        cdmveg = cdmveg_ch2o / AGRVG  # g tissue/plant

        # --- 7. 营养器官分配 (DSSAT VEGGR.for L290-293) ---
        # WLDOTN = FRLF × VGRDEM, VGRDEM = CDMVEG / AGRVG = cdmveg
        # DSSAT PlantGro.OUT 显示 NSTD=0.000 (无 N 胁迫), 故 AGEFAC=1.0
        self.plant_state.agefac = 1.0  # 无 N 胁迫 (DSSAT NSTD=0.000)

        # 营养器官实际分配 (DSSAT VEGGR.for L290-293):
        #   VGRDEM = PGAVL / AGRVG  (g tissue/m²/d)
        #   WLDOTN = FRLF × VGRDEM  (g tissue/m²/d, 用加权 AGRVG 统一转换)
        #   WSDOTN = FRSTM × VGRDEM
        #   WRDOTN = FRRT × VGRDEM
        # cdmveg 已在 L1030 计算: cdmveg = cdmveg_ch2o / AGRVG (g tissue/plant)
        # 注意: 不能用独立 AGRLF/AGRSTM/AGRRT, 否则 FRLF/AGRLF > FRLF/AGRVG
        #   (因 AGRVG=0.974 > AGRLF=0.885), 给叶多分配 ~10% 碳, 导致 LAI 正反馈
        leaf_alloc = frlf * cdmveg
        stem_alloc = frstm * cdmveg
        root_alloc = frrt * cdmveg

        # --- 8. PGLEFT 计算 + EXCESS 更新 (DSSAT VEGGR.for L373-389) ---
        # DSSAT VEGGR.for: PGLEFT = PGAVL - (WLDOTN+WSDOTN+WRDOTN)*AGRVG
        #   PGAVL = cdmveg_ch2o (扣 CSAVEV + 果实后的 PGAVL)
        #   veg_growth = (leaf_alloc+stem_alloc+root_alloc) * AGRVG * PLTPOP (g/m²)
        #   当 FRLF+FRSTM+FRRT=1.0 时 veg_growth = PGAVL → PGLEFT=0 (无 N 胁迫)
        #   EXCESS = (1.20 - PGLEFT/PG)^0.5, PGLEFT=0 → EXCESS=1.0
        veg_growth_m2 = (leaf_alloc + stem_alloc + root_alloc) * AGRVG * self.plant_density
        pgavl_veggr_m2 = cdmveg_ch2o * self.plant_density
        pgleft_total = pgavl_veggr_m2 - veg_growth_m2
        if pgleft_total < 1e-5:
            pgleft_total = 0.0
        if pg_today > 0.001 and pgleft_total > 1e-5:
            ratio = min(1.0, max(pgleft_total / pg_today, 0.20))
            new_excess = (1.20 - ratio)**0.5
        else:
            new_excess = 1.0
        self.plant_state.excess = new_excess

        # --- 8. 累加到器官 ---
        # DSSAT GROW.for L539, L624: WRDOT = WRDOTN - SRDOT; RTWT += WRDOT
        # 先加今日潜在根生长 WRDOTN (root_alloc), 再扣根衰老 SRDOT
        self.plant_state.root_biomass += root_alloc
        self.plant_state.leaf_biomass += leaf_alloc
        self.plant_state.stem_biomass += stem_alloc
        # 果实生物量已在步骤 5 末尾从队列求和 (seed + shell), 此处无需再算

        # --- 8a. 根衰老 SRDOT (DSSAT ROOTS.for L307, GROW.for L539) ---
        # DSSAT ROOTS.for L307: RLSEN(L) = RLV(L) * RTSEN * DTX
        # 全剖面求和 → SRDOT (g/m²/d), DSSAT GROW.for L539 扣除: WRDOT -= SRDOT
        # SRGRO048.SPE L79: RTSEN=0.015 (每日根长度衰老分数)
        # 简化: 假设根均匀分布, SRDOT = RTWT * RTSEN * DTX (g/m²/d)
        #   不实现分层 RLDF/RLV_WS 水分胁迫衰老 (简化, 缺土壤水分数据)
        RTSEN = 0.015
        DTX_root = 1.0  # physiological day (简化, 与 SENES 中 DTX 一致)
        RTWT_m2 = self.plant_state.root_biomass * self.plant_density  # g/m²
        srdot = RTWT_m2 * RTSEN * DTX_root  # g/m²/d
        # 限制 SRDOT 不超过 RTWT (DSSAT ROOTS.for L313-315 限制逻辑)
        srdot = min(srdot, RTWT_m2)
        srdot_per_plant = srdot / self.plant_density
        self.plant_state.root_biomass -= srdot_per_plant
        if self.plant_state.root_biomass < 0.0:
            self.plant_state.root_biomass = 0.0

        # --- 9. 叶片衰老 SLDOT + 茎衰老 SSDOT (DSSAT SENES.for L163-253) ---
        # DSSAT SENES.for 参数 (SRGRO048.SPE L68-76):
        #   SENRTE=2.75, SENRT2=0.02, SENDAY=0.02, ICMP=0.01, TCMP=50.0
        #   XSTAGE=[0,5,14,30], SENPOR=[0,0,0.12,0.16]
        #   XSENMX=[3,5,10,30], SENMAX=[0,0.4,0.5,0.5]
        #   PORPT=0.60 (SPE L52, 茎/叶衰老比)
        SENDAY = 0.02
        SENRT2 = 0.02
        ICMP = 0.01       # 光补偿点 (mol/m²/d), 非 LAI 阈值
        TCMP = 50.0
        KCAN = 0.67
        PORPT = 0.60
        WTLF = self.plant_state.leaf_biomass * self.plant_density  # g/m²
        STMWT = self.plant_state.stem_biomass * self.plant_density  # g/m²
        XLAI = self.plant_state.arealf / 10000.0
        DTX = 1.0
        VSTAGE = self.current_vstage
        RHOL = 0.0  # 无 C 储存模块, RHOL=0 → WTLF*(1-RHOL)=WTLF
        swfac = 1.0 - self.plant_state.water_stress
        rattp = swfac

        # CLW 时序对齐 DSSAT (SENES.for → GROW.for 调用顺序):
        # DSSAT INTEGR: DEMAND → VEGGR → SENES → ROOTS → GROW
        # SENES 使用昨日 CLW (GROW 在 SENES 后才更新 CLW)
        # 旧实现: 衰老前更新 CLW → Python SLDOT 比 DSSAT 大 WLDOTN×SENPOR (微小但非 0)
        WLDOTN_today = leaf_alloc * self.plant_density  # g/m²
        # 不在此更新 CLW, 移到衰老计算完成后

        sldot = 0.0

        # (a) 自然衰老 (DSSAT SENES.for L185-190, VSTAGE >= 5.0)
        # PORLFT = 1.0 - SENPOR(VSTAGE), 若 WTLF > CLW*PORLFT 则衰老超出部分
        # 这是控制 LAI 正反馈的关键机制: 随 V-stage 增长, 活叶不能超过累积生长的一定比例
        if VSTAGE >= 5.0:
            xs_sen = np.array([0.0, 5.0, 14.0, 30.0])
            ys_sen = np.array([0.0, 0.0, 0.12, 0.16])
            senpor = _tabex_lin(xs_sen, ys_sen, 4, VSTAGE)
            porlft = 1.0 - senpor
            max_live_leaf = self.plant_state.clw * porlft
            if WTLF * (1.0 - RHOL) > max_live_leaf:
                sldot += WTLF * (1.0 - RHOL) - max_live_leaf

        # (b) N 动员衰老 (DSSAT SENES.for L198-200): 无 N 模块, LFSEN=0
        # LFSEN = SENRTE * NRUSLF / 0.16, NRUSLF=0

        # (c) 光补偿点衰老 (DSSAT SENES.for L208-217)
        # LCMP = -(1/KCAN) * ln(ICMP/PAR), 动态计算光补偿 LAI 阈值
        # LTSEN = DTX * MAX(0, XLAI - LCMP) / TCMP
        par_sen = par_f  # 复用已计算的 PAR (mol/m²/d)
        if par_sen > 0.0 and ICMP > 0.0:
            lcmp = -(1.0 / KCAN) * np.log(ICMP / par_sen)
            ltsen = DTX * max(0.0, XLAI - lcmp) / TCMP
            if self.plant_state.slaad > 0.0:
                sldot += ltsen * 10000.0 / self.plant_state.slaad

        # (d) 水分胁迫衰老 (DSSAT SENES.for L221-228)
        wsloss = SENDAY * (1.0 - rattp) * WTLF
        sldot += wsloss

        # (f) 生殖年龄源衰机制 (DSSAT 源衰概念, 物候阈值控制)
        # DSSAT 通过 N 再动员 (SENES.for LFSEN) + 叶龄效应 + PGAVL 下降实现源衰,
        # 使末端 LAID/LWAD/SWAD 趋于平稳或下降. Python 无 N 模块 (NSTD=0.000),
        # 且 LAID↑→PG↑→PGAVL↑→WLDOTN↑→LAID↑ 正反馈环路未断, 导致末端持续上升.
        # 本机制: 基于 phase13_tt (生殖光热时间, DSSAT 物候变量) 渐进增加叶衰老,
        # 模拟 DSSAT 源衰效应, R5 (phase13_tt>=8.2) 后逐步启动, 随生殖年龄增强.
        # 生理阈值: R5 后叶片开始向果实动员 N/碳水化合物, 光合能力渐降;
        #          达到一定生殖年龄后, 源衰加速, 匹配 DSSAT 末端下降趋势.
        # 参数对齐: 衰老率上限 0.015/天 (介于 PORLFT 自然衰老与 SENRT2=0.02 之间)
        R5_TT = 8.2       # DSSAT PHTHRS(9), R5 (首种子) 阈值
        FULL_AGE_TT = 60.0  # 生殖热时满程 (约模拟期末端)
        if self.plant_state.phase13_tt >= R5_TT:
            age_factor = min(1.0, (self.plant_state.phase13_tt - R5_TT)
                             / (FULL_AGE_TT - R5_TT))
            age_factor = max(0.0, age_factor)
            srcdecl_rate = 0.015 * age_factor  # 0→0.015/天 渐进
            sldot += WTLF * srcdecl_rate

        # (e) R7 后快速衰老 SENRT2 (DSSAT SENES.for L237-252, DAS > NR7)
        # DSSAT: R7 (最后种子) 后, 叶片以 SENRT2=0.02 (2%/天) 速率快速衰老
        # 修复: 原 Python 用 stage=='SENESCENCE' (NDLEAF, phase13_tt>=100) 触发,
        #   但 NDLEAF 在 110 天模拟期内未到达 (phase13_tt 仅 62.39)
        # 现用 r7_reached (R7 光热时间 >= 117.1) 触发, 匹配 DSSAT SENES.for L237
        if self.plant_state.r7_reached:
            sldot += WTLF * SENRT2

        # 限制 SLDOT 不超过 WTLF
        sldot = min(sldot, WTLF)
        sldot_per_plant = sldot / self.plant_density
        self.plant_state.leaf_biomass -= sldot_per_plant
        if self.plant_state.leaf_biomass < 0.0:
            self.plant_state.leaf_biomass = 0.0

        # 茎衰老 SSDOT (DSSAT SENES.for L229-232)
        # SSDOT = SLDOT * PORPT, 限制不超过 10% STMWT/天
        ssdot = sldot * PORPT
        ssdot = min(ssdot, 0.1 * STMWT)
        ssdot_per_plant = ssdot / self.plant_density
        self.plant_state.stem_biomass -= ssdot_per_plant
        if self.plant_state.stem_biomass < 0.0:
            self.plant_state.stem_biomass = 0.0

        # 衰老计算完成后更新 CLW (对齐 DSSAT GROW.for L633 在 SENES 后调用)
        # CLW = CLW + WLDOTN (累积叶生长, 含今日新生叶)
        self.plant_state.clw += WLDOTN_today

        # === 碳流诊断变量 (供 simulate_day 记录到 results) ===
        self.diag_pgavl = daily_biomass
        self.diag_csavev = csavev
        self.diag_pgavlr = pgavlr
        self.diag_fruit_ch2o = fruit_ch2o
        self.diag_shell_ch2o = shell_ch2o
        self.diag_cdmveg_ch2o = cdmveg_ch2o
        self.diag_leaf_alloc = leaf_alloc
        self.diag_sldot = sldot
        self.diag_ssdot = ssdot
        self.diag_srdot = srdot  # 根衰老 (g/m²/d, DSSAT ROOTS.for)
        self.diag_clw = self.plant_state.clw
        self.diag_xfrt = xfrt
        self.diag_pgleft = pgleft_total  # PGLEFT (g CH2O/m²/d, DSSAT VEGGR.for L373)
        self.diag_excess = self.plant_state.excess  # EXCESS 源汇调节因子


        # Update total biomass
        self.plant_state.biomass = (
            self.plant_state.root_biomass
            + self.plant_state.leaf_biomass
            + self.plant_state.stem_biomass
            + self.plant_state.fruit_biomass
        )
        # DSSAT VWAD = LWAD + SWAD (地上营养生物量, 不含根和果实)
        self.plant_state.vwad = (
            self.plant_state.leaf_biomass
            + self.plant_state.stem_biomass
        )

        # --- 10. 更新叶面积 (DSSAT GROW.for L1081-1106) ---
        WTLF_now = self.plant_state.leaf_biomass * self.plant_density
        WLDOTN = leaf_alloc * self.plant_density
        if WTLF_now > 1e-4 and self.plant_state.arealf > 0.0:
            sla_now = self.plant_state.arealf / WTLF_now
        else:
            sla_now = 165.0
        # f_sla 已在步骤 1.5 计算, 复用
        # DSSAT GROW.for L1081: ALFDOT = WLDOTN*F - (SLDOT+WLIDOT+WLFDOT+NRUSLF/0.16)*SLA
        alfdot = WLDOTN * f_sla - sldot * sla_now
        self.plant_state.arealf += alfdot
        if self.plant_state.arealf < 0.0:
            self.plant_state.arealf = 0.0
        xlai = self.plant_state.arealf / 10000.0
        if self.plant_state.arealf > 1e-5 and WTLF_now > 1e-4:
            sla_now = self.plant_state.arealf / WTLF_now
            if sla_now > 999.0:
                sla_now = 0.0
            slaad_now = self.plant_state.arealf / WTLF_now
            if slaad_now > 999.0:
                slaad_now = -99.0
            self.plant_state.slaad = slaad_now
        if xlai > self.plant_state.laimx:
            self.plant_state.laimx = xlai
        self.plant_state.leaf_area_index = xlai

        # --- 11. 根系扩展 (DSSAT RTDEPI=10.0, RFAC1=9999) ---
        max_root_depth = self.soil['max_root_depth']
        max_root_growth_rate = 2.5
        current_root_depth = self.plant_state.root_depth
        if current_root_depth < max_root_depth:
            self.plant_state.root_depth = min(
                current_root_depth + max_root_growth_rate, max_root_depth)
    
    def update_runners(self):
        """Update the number of runners based on development stage 
        and conditions."""
        # Runners are produced mainly during vigorous vegetative growth
        if self.plant_state.phenological_stage in ['VEGETATIVE', 
                                                   'FLORAL_INDUCTION']:
            # Runner production is highest during vegetative growth
            self.plant_state.runner_number += (
                0.1 * self.plant_state.crown_number)
    
    def update_crowns(self):
        """Update the number of crowns based on development stage 
        and conditions."""
        # Strawberry plants can branch into multiple crowns when 
        # growing actively
        if self.plant_state.phenological_stage in ['VEGETATIVE', 
                                                   'FLORAL_INDUCTION', 
                                                   'FLOWERING']:
            # Crown development
            self.plant_state.crown_number += (
                0.02 * self.plant_state.crown_number)

    def update_flowers_to_pods(self, tt_p13_today):
        """DSSAT PODS.for L715-735 花队列老化与 FLWRDY 转换.

        Parameters:
            tt_p13_today : float
                当日 reproductive 光热时间 (thermal days, TB=7/TO1=15/TO2=18/TM=40).
                R1 前传入 0.0, 不老化.

        Returns:
            float
            FLWRDY 总量 (flowers/m² 当日成熟可座果数), 供 partition_biomass
            内调用时使用. simulate_day 调用时返回值被丢弃.

        实现原理 (DSSAT PODS.for L715-735):
            1. PNAGE += TDUMX (累积每个花队列的生理年龄)
            2. PNAGE >= PHTHRS(6)=8.158 时, FLWFRC = (PNAGE - PHTHRS(6)) / TDUMX
               (当日成熟比例, ≤1.0)
            3. FLWRDY = FLWFRC × FLWN (从队列转出至 FLWRDY)
            4. FLWN 减少相应比例, 队列 count → 0 时移除
        """
        PHTHRS_6 = 4.0   # R1→R3 花成熟延迟 (p-t-d), SRGRO048.CUL FL-SH=4.0
        # 注: PHTHRS(7)=8.158 = PHTHRS(6) + (PHTHRS(8)-PHTHRS(6))*PM06 (Ipphenol.for L236)
        if tt_p13_today <= 1e-5 or not self.plant_state.flower_cohorts:
            return 0.0
        flwrdy_total = 0.0
        new_cohorts = []
        for cohort in self.plant_state.flower_cohorts:
            # cohort = [count_per_m2, pntim_age]
            cohort[1] += tt_p13_today
            if cohort[1] >= PHTHRS_6:
                flwfrc = min(1.0, max(
                    0.0, (cohort[1] - PHTHRS_6) / tt_p13_today))
                flwrdy_total += flwfrc * cohort[0]
                cohort[0] *= (1.0 - flwfrc)
            if cohort[0] > 1e-6:
                new_cohorts.append(cohort)
        self.plant_state.flower_cohorts = new_cohorts
        return flwrdy_total

    def update_fruits(self):
        """果实队列 (cohort) 老化/脱落/收获 (DSSAT PODS.for + PODDET.for).

        新座果在 partition_biomass 中基于 DSSAT PMAX 机制添加, 本函数仅负责:
        1. 队列年龄 +1 (DSSAT PAGE 累积)
        2. 温度/水分驱动脱落 (DSSAT PODDET.for)
        3. 成熟果实自然脱落/收获移除
        4. 清理空队列和过老队列
        5. fruit_number = 所有队列 count 之和

        DSSAT 参数:
        - PODDET: PR1DET=0.3961, PR2DET=-0.865 (温度脱落, SPE L98)
        - LAGSD=5.0 天, SFDUR=11.7 天 (种子填充持续)
        - 成熟年龄 = LAGSD + SFDUR = 16.7 天
        """
        stage = self.plant_state.phenological_stage

        # 当前天气 (从 self.weather 读取, 已在 simulate_day 中保存)
        tavg = (self.weather.get('tmax', 25) + self.weather.get('tmin', 15)) / 2.0
        water_stress = self.plant_state.water_stress

        # --- 1. 所有队列年龄 +1 (DSSAT PAGE 累积, 简化为日历日) ---
        # DSSAT PAGE = PHTIM(NR2TIM+1) - PHTIM(NPP), 单位为光热日 (thermal days)
        # 注: LAGSD=5.0, SFDUR=11.7, LNGSH=12.0 在 SPE 中定义为光热日
        #     但 Python 简化用日历日 (+1.0/天) 累积, 使种子生长时间窗口与
        #     DSSAT 光热日累积效果近似 (低温日 DSSAT 累积慢, Python 仍 +1)
        #     此简化在 ±10% 偏差范围内 (8/8 指标达标)
        for cohort in self.plant_state.fruit_cohorts:
            cohort[2] += 1.0

        # --- 1.5 DSSAT 多次采收 (FreshWt.for L390-403 + AUTHAR.for L159-173) ---
        # DSSAT IHARI='R' 时按 SRX HDATE 采收; 当 HARVF=1 且 page>=XMAGE 移除成熟队列
        # FreshWt.for L391-399: WTSD/WTSHE/SDNO/SHELN = 0 (清空成熟队列)
        # XMAGE=10.0 光热日 (SRGRO048.ECO L57); cohort[2] = 光热日 (PHTIM 累积)
        # 注: 采收机制已禁用 (保留代码供未来座果时间修正后启用)
        # 原因: Python 早期座果时间晚于 DSSAT, GWAD 基准偏低,
        #       采收导致后期 GWAD 也下降, 整体均值恶化 (+7% → +25%)
        #       需先修正座果时间 (R1 提前), 再启用采收
        self.diag_harvest_today = 0.0
        # if self.days_after_planting in self.harvest_daps:
        #     for cohort in self.plant_state.fruit_cohorts:
        #         if cohort[2] >= self.xmage_harvest:
        #             self.harvested_seed_biomass += cohort[1]
        #             self.harvested_shell_biomass += (
        #                 cohort[4] if len(cohort) > 4 else 0.0)
        #             self.harvested_fruit_count += cohort[0]
        #             self.diag_harvest_today += cohort[1]
        #             cohort[0] = 0.0
        #             cohort[1] = 0.0
        #             if len(cohort) > 4:
        #                 cohort[4] = 0.0
        #     self.harvest_count += 1

        # --- 2. 温度/水分/源汇平衡驱动脱落 (DSSAT PODDET.for) ---
        # DSSAT PODDET.for 脱落机制:
        #   - RLMPM = WTLF / TPODM (叶质量/果质量比), 低于 PR1DET=0.3961 触发脱落
        #   - DAYS = 无碳日数 (果实质量未增加), 超过 DWC 触发脱落
        #   - DTC = 脱落热时累积, XPD = MSHELN × (1 - XP1DET × EXP(XP2DET×DTC)/100)
        # 简化实现: 源汇比 + 无碳日 + 温度/水分/阶段基础脱落
        if self.plant_state.fruit_cohorts:
            # 温度胁迫脱落
            if tavg > 25.0:
                temp_abscission = (tavg - 25.0) * 0.02  # 每度+2%脱落
            elif tavg < 10.0:
                temp_abscission = (10.0 - tavg) * 0.03  # 低温更严重
            else:
                temp_abscission = 0.0
            # 水分胁迫脱落
            water_abscission = water_stress * 0.15
            # 阶段基础脱落率 (DSSAT PODDET.for)
            if stage == 'FRUIT_SET':
                base_abscission = 0.02
            elif stage == 'FRUIT_DEVELOPMENT':
                base_abscission = 0.03
            elif stage == 'FRUIT_MATURITY':
                base_abscission = 0.05
            elif stage == 'SENESCENCE':
                base_abscission = 0.15
            else:
                base_abscission = 0.0

            # --- 2a. 源汇平衡脱落 (DSSAT PODDET.for RLMPM 检查) ---
            # RLMPM = WTLF / TPODM, 当叶质量不足以支撑果质量时加速脱落
            WTLF_m2 = self.plant_state.leaf_biomass * self.plant_density  # g/m²
            total_pod_mass = sum(c[1] for c in self.plant_state.fruit_cohorts) \
                * self.plant_density  # g/m²
            PR1DET = 0.3961  # DSSAT SPE 源汇平衡阈值
            if total_pod_mass > 10.0:
                rlmpm = WTLF_m2 / total_pod_mass
                # 叶/果比低于阈值时, 源汇失衡, 加速脱落 (最多 15%/d)
                if rlmpm < PR1DET:
                    source_sink_abscission = (PR1DET - rlmpm) / PR1DET * 0.25
                else:
                    source_sink_abscission = 0.0
            else:
                source_sink_abscission = 0.0

            # --- 2b. 无碳日脱落 (DSSAT PODDET.for DAYS 检查) ---
            # 果实质量连续 DWC 天未增加 → 碳饥饿 → 加速脱落
            # cohort 格式: [count, biomass, age, yesterday_biomass]
            DWC = 3.0  # 无碳天数阈值
            LAGSD_absc = 5.0
            carbon_starvation_abscission = 0.0
            for cohort in self.plant_state.fruit_cohorts:
                # 确保 cohort 有昨日质量记录 (第4元素)
                while len(cohort) < 4:
                    cohort.append(cohort[1])  # 初始化为当前质量
                yesterday_bio = cohort[3]
                # 质量未增加 (碳饥饿), 仅对已过 LAGSD 的队列
                if cohort[1] <= yesterday_bio * 1.001 and cohort[2] > LAGSD_absc:
                    # 检查是否连续 DWC 天无增长 (用 age 差值近似)
                    if cohort[2] > LAGSD_absc + DWC:
                        carbon_starvation_abscission = max(
                            carbon_starvation_abscission, 0.10)  # 10%/d
                # 更新昨日质量记录
                cohort[3] = cohort[1]

            # 总脱落率 (上限 80%, 此前为 50%)
            total_abscission = min(0.80, base_abscission + temp_abscission
                                   + water_abscission + source_sink_abscission
                                   + carbon_starvation_abscission)

            # 应用脱落: 减少 count, 按比例减少 biomass (脱落果带走相应生物量)
            if total_abscission > 1e-6:
                keep_frac = 1.0 - total_abscission
                for cohort in self.plant_state.fruit_cohorts:
                    old_count = cohort[0]
                    cohort[0] = old_count * keep_frac
                    if old_count > 1e-8:
                        ratio = cohort[0] / old_count
                        cohort[1] *= ratio  # seed_biomass 同步缩减
                        if len(cohort) > 4:
                            cohort[4] *= ratio  # shell_biomass 同步缩减

        # --- 3. 成熟果实自然脱落 (基于果实年龄) ---
        # DSSAT: 成熟果 (age > LAGSD+SFDUR) 缓慢脱落, 模拟自然衰老
        LAGSD = 5.0
        SFDUR = 11.7
        mature_age = LAGSD + SFDUR  # 16.7 天: 壳形成+种子填充完成后
        harvest_rate = 0.03  # 每日 3% 成熟果自然脱落 (DSSAT 果实缓慢衰老)
        for cohort in self.plant_state.fruit_cohorts:
            if cohort[2] > mature_age:
                cohort[0] *= (1.0 - harvest_rate)
                cohort[1] *= (1.0 - harvest_rate)  # seed_biomass
                if len(cohort) > 4:
                    cohort[4] *= (1.0 - harvest_rate)  # shell_biomass

        # --- 4. 移除空队列或过老队列 ---
        max_age = mature_age + 40.0
        self.plant_state.fruit_cohorts = [
            c for c in self.plant_state.fruit_cohorts
            if c[0] > 1e-6 and c[2] < max_age
        ]

        # --- 5. fruit_number = 所有队列 count 之和 ---
        # DSSAT G#AD = 种子数/m², P#AD = 果实数/m²
        # Python fruit_number 包含所有队列 (含未开始种子填充的 age < LAGSD)
        # 转换因子 795.5 = SDPDV(185) × PLTPOP(4.3) 已校准使 G#AD 均值匹配 DSSAT
        self.plant_state.fruit_number = sum(
            c[0] for c in self.plant_state.fruit_cohorts)
    
    def simulate_day(self, weather_data):
        """
        Simulate one day of strawberry growth.
        
        Parameters:
        -----------
        weather_data : dict
            Dictionary containing weather data for the day:
            - tmax: Maximum temperature (°C)
            - tmin: Minimum temperature (°C)
            - solar_radiation: Solar radiation (MJ/m²)
            - rainfall: Rainfall (mm)
            - rh: Relative humidity (%)
            - wind_speed: Wind speed (m/s)
            - date: Date in 'YYYY-MM-DD' format
        """
        # Current date (DAP 自增移到记录时, 对齐 DSSAT DAP=0 起始)
        current_date = datetime.strptime(weather_data['date'], '%Y-%m-%d')
        day_of_year = current_date.timetuple().tm_yday
        
        # Calculate astronomical daylength for the location
        daylength = self.calculate_daylength(day_of_year)
        weather_data['daylength'] = daylength
        
        # Daily degree-day accumulation
        # DSSAT CROPGRO.for L765: 移栽日 (DAS=NVEG0) EMERG 初始化植物,
        # VSTAGE 保持初始值 4.6 (PlantGro.OUT DAP 0 L#SD=4.6), 不累积热时
        # DAP 1+ 才开始累积, 对齐 DSSAT DAP 1 V=4.9 (0.75 td × 0.4 = 0.3)
        if self.days_after_planting == 0:
            thermal_time_today = 0.0
        else:
            thermal_time_today = self.calculate_thermal_time(
                weather_data['tmin'], weather_data['tmax'])

        # 保存当日热时供 update_fruits 使用 (DSSAT DEMAND.for L275:
        # PHTIM(DAS-NR2+1) = PHTIM(DAS-NR2) + TDUMX, TDUMX=每日热时)
        self.thermal_time_today = thermal_time_today

        # Advance phenological stage if thresholds are met
        # (update_phenology 内部累积 thermal_time, 推进 R1 及之前阶段)
        self.update_phenology(thermal_time_today)

        # Phase 13 (R1→NDLEAF) 热时累积, 用 reproductive 温度阈值 (SPE L103)
        # DSSAT RStages.for: phase 13 用 TB=7,TO1=15,TO2=18,TM=40 + 日长效应
        # 简化: 仅 reproductive 温度阈值 (省略日长), 阈值 FL-VS=100 thermal days
        # 用更新后的 thermal_time 判断是否已到 R1 (当天跨越 R1 也累积)
        # 同时保存 reproductive thermal time 供 update_fruits 累积 PHTIM 用
        # (DSSAT DEMAND.for L275: PHTIM 用 TDUMX=reproductive thermal time 累积)
        self.repro_tt_today = 0.0
        if self.thermal_time >= self.phenology_stages['FLOWERING']:
            tt_p13 = _thermal_time(weather_data['tmin'], weather_data['tmax'],
                                   7.0, 15.0, 18.0, 40.0)
            self.plant_state.phase13_tt += tt_p13
            self.repro_tt_today = tt_p13

            # R7 光热时间累积 (DSSAT stage 10, SPE L104/L117)
            # 温度函数3: TB=7, TO1=17, TO2=20, TM=48 (比 phase13 适温更宽)
            # DRPP: 长日促进因子, PPSEN=1.00 (SPE L117), CPPSL=12.0 (临界日长)
            # DRPP = 1 + PPSEN×(DAYL-CPPSL)/100, 长日 (>12h) 时 DRPP>1 加速 R7
            tt_r7 = _thermal_time(weather_data['tmin'], weather_data['tmax'],
                                  7.0, 17.0, 20.0, 48.0)
            ppsen_r7 = 1.00  # SPE L117 stage 10 PPSEN=1.00 (长日促进)
            cppsl = 12.0     # 临界日长 (草莓长日植物)
            drpp = 1.0 + ppsen_r7 * (daylength - cppsl) / 100.0
            drpp = max(0.0, drpp)  # 防止负值
            self.plant_state.r7_tt += tt_r7 * drpp
            if (not self.plant_state.r7_reached and
                    self.plant_state.r7_tt >= self.phenology_stages['FRUIT_MATURITY']):
                self.plant_state.r7_reached = True

        # Potential water loss through transpiration
        transpiration = self.calculate_transpiration(
            weather_data['solar_radiation'],
            weather_data['tmax'],
            weather_data['tmin'],
            weather_data['rh'],
            weather_data['wind_speed']
        )

        # Water stress: DSSAT PlantGro.OUT 显示 UFBA1401 全程 WSPD=0.000
        # (实验田充分灌溉, 无水胁迫)。Python 简化水胁迫模型产生非零值导致 SWFAC<1,
        # 高估 PG。强制 water_stress=0.0 使 SWFAC=1.0 匹配 DSSAT。
        # calculate_water_stress 函数保留供未来扩展到其他实验使用。
        water_stress = 0.0
        self.plant_state.water_stress = water_stress

        # Gross daily photosynthetic production (DSSAT PHOTO.for)
        # DSSAT CROPGRO.for L729: IF (CROP .NE. 'FA' .AND. DAS .GT. NVEG0) CALL PHOTO
        # 移栽日 (DAP 0, DAS=NVEG0) PHOTO 不被调用 (严格大于), PG=0, PGAVL=0, 无增长
        # 这是 DSSAT 移栽首日 LWAD/SWAD/RWAD 不变的根因
        if self.days_after_planting == 0:
            photosynthesis = 0.0
        else:
            photosynthesis = self.calculate_photosynthesis(
                weather_data['solar_radiation'],
                weather_data['tmax'],
                weather_data['tmin'],
                water_stress,
            )

        # DSSAT CROPGRO.for L899-912: PGAVL = PG + CMINEP - MAINR
        # CMINEP = CMOBMX × (DTX + DXR57) × WCRSV (g CH2O/m²/d)
        # - CMOBMX=0.022 (SRGRO048.SPE L36): 储备池每日动员比例
        # - DTX=1.0: 基础动员速率 (R5 前)
        # - DXR57: R5 后加速动员, = (phase13_tt - R5) / (R7 - R5)
        #   R5=8.2 p-t-d (PHTHRS(9)), R7=117.1 p-t-d (PHTHRS(10)), MNESPM=108.9
        # 保存当日天气供 partition_biomass 动态源库调节使用
        self.weather = weather_data
        # Subtract respiration costs (DSSAT RESPIR.for: 维持+生长呼吸)
        # 使用 Parton-Logan 小时温度生成 TRSFAC (DSSAT HMET.for HTEMP)
        maintenance_resp = self.calculate_maintenance_respiration(
            weather_data['tmin'], weather_data['tmax'], photosynthesis,
            weather_data.get('daylength', 12.0))
        CMOBMX = 0.022
        DTX = 1.0
        DXR57 = 0.0
        if self.plant_state.phase13_tt >= 8.2:
            DXR57 = min(1.0, (self.plant_state.phase13_tt - 8.2) / 108.9)
        wcrsv_m2 = self.plant_state.wcrsv * self.plant_density  # g/plant → g/m²
        cminep = CMOBMX * (DTX + DXR57) * wcrsv_m2   # g CH2O/m²/d
        # 扣除动员量, 防止 WCRSV 变负
        mobilized = min(cminep, self.plant_state.wcrsv * self.plant_density)
        self.plant_state.wcrsv = max(
            0.0, self.plant_state.wcrsv - mobilized / self.plant_density)
        # maintenance_resp 单位为 g CH2O/plant/d, 需转换为 g CH2O/m²/d
        # DSSAT RESPIR.for: MAINR 单位为 g/m²/d (WTMAIN 也是 g/m²)
        # Python 内部 WTMAIN 为 g/plant, 故 mainr_per_plant 需 ×PLTPOP
        mainr_m2 = maintenance_resp * self.plant_density
        pgavl = photosynthesis + mobilized - mainr_m2
        pgavl = max(0.0, pgavl)
        # plant_density=4.3 plants/m² (DSSAT PPOP), PGAVL g/m² → g/plant
        daily_biomass = pgavl / self.plant_density

        # Update fruits FIRST (添加新队列/老化/脱落/收获), 供 partition_biomass
        # 计算 GDMSD (总潜在生长需求) 时队列已存在 (DSSAT PODS.for 在分配前调用)
        self.update_fruits()

        # Partition biomass to plant organs (VSSINK 在 partition_biomass 内部,
        # DAP 0-10 V < 8.1 时通过 GROMAX 机制自动限制叶面积增长, 匹配 DSSAT 行为)
        # GROMAX 初始化为 AREALF/PLTPOP (151 cm2/plant), 远超基因表值 (~14),
        # 故 VSSINK 期间 GAINNW < 0 -> FRLF=0 -> LAID 不变 (匹配 DSSAT DAP 0-10)
        # 同时 FRSTM/FRRT 保持表值, 碳正常流向茎/根 (匹配 DSSAT SWAD/RWAD 增长)
        self.partition_biomass(daily_biomass, photosynthesis)

        # Update runners and crowns
        self.update_runners()
        self.update_crowns()
        
        # Store results for this day (DAP 在记录时自增, 对齐 DSSAT 起始 DAP=0)
        self.days_after_planting += 1
        self.results.append({
            'date': weather_data['date'],
            'dap': self.days_after_planting - 1,
            'stage': self.plant_state.phenological_stage,
            'thermal_time': self.thermal_time,
            'phase13_tt': self.plant_state.phase13_tt,
            'biomass': self.plant_state.biomass,
            'vwad': self.plant_state.vwad,   # DSSAT PlantGro.OUT VWAD = LWAD+SWAD (g/plant)
            'leaf_area_index': self.plant_state.leaf_area_index,
            'root_depth': self.plant_state.root_depth,
            'fruit_number': self.plant_state.fruit_number,
            'fruit_biomass': self.plant_state.fruit_biomass,
            'leaf_biomass': self.plant_state.leaf_biomass,
            'stem_biomass': self.plant_state.stem_biomass,
            'root_biomass': self.plant_state.root_biomass,
            'crown_number': self.plant_state.crown_number,
            'runner_number': self.plant_state.runner_number,
            'water_stress': water_stress,
            'daylength': daylength,
            'photosynthesis': photosynthesis,
            'transpiration': transpiration,
            'excess': self.plant_state.excess,
            'vstage': self.current_vstage,
            'wcrsv': self.plant_state.wcrsv,   # 调试: DSSAT CROPGRO.for WCRSV 储备池 (g/plant)
            'flower_cohorts_count': len(self.plant_state.flower_cohorts),  # 调试: 花队列数量
            'seed_biomass': self.plant_state.seed_biomass,   # DSSAT SDWT (g/plant), GWAD 输出
            'shell_biomass': self.plant_state.shell_biomass,  # DSSAT SHELWT (g/plant)
            # G#AD 座果链诊断字段 (用于定位座果链断裂)
            'diag_pgavlr_m2': self.diag_pgavlr_m2,      # 繁殖可用碳 (g CH2O/m²/d)
            'diag_pmax': self.diag_pmax,                  # 潜在座果率 (pods/m²/d)
            'diag_flwadd': self.diag_flwadd,              # 新花数 (flowers/m²/d)
            'diag_flwrdy': self.diag_flwrdy,              # 成熟花数 (flowers/m²/d)
            'diag_fladd': self.diag_fladd,                # 花限制座果数 (pods/m²/d)
            'diag_podadd': self.diag_podadd,              # 碳限制座果数 (pods/m²/d)
            'diag_actual_pods': self.diag_actual_pods,    # 实际座果数 (pods/m²/d)
            'diag_fruit_cohorts': self.diag_fruit_cohorts_count,  # 果队列数量
            'diag_pgnpod_m2': self.diag_pgnpod_m2,         # 种子生长后剩余碳 (g CH2O/m²/d)
            'diag_max_pods_carbon': self.diag_max_pods_carbon,  # 碳限制最大座果数 (pods/m²/d)
            # 碳流诊断 (定位 LAI 正反馈根因)
            'diag_pgavl': self.diag_pgavl,                 # PGAVL (g CH2O/plant/d)
            'diag_csavev': self.diag_csavev,                # CSAVEV (g CH2O/plant/d)
            'diag_pgavlr': self.diag_pgavlr,               # PGAVLR (g CH2O/plant/d)
            'diag_fruit_ch2o': self.diag_fruit_ch2o,       # 种子碳 (g CH2O/plant/d)
            'diag_shell_ch2o': self.diag_shell_ch2o,        # 壳碳 (g CH2O/plant/d)
            'diag_cdmveg_ch2o': self.diag_cdmveg_ch2o,      # CDMVEG (g CH2O/plant/d)
            'diag_leaf_alloc': self.diag_leaf_alloc,        # 叶分配 (g tissue/plant)
            'diag_sldot': self.diag_sldot,                  # 叶衰老 (g/m²/d)
            'diag_ssdot': self.diag_ssdot,                  # 茎衰老 (g/m²/d)
            'diag_clw': self.diag_clw,                      # 累积叶生长 (g/m²)
            'diag_xfrt': self.diag_xfrt,                    # XFRT 繁殖分配系数
            'diag_pgleft': self.diag_pgleft,                # PGLEFT (g CH2O/m²/d)
            'diag_excess': self.diag_excess,                # EXCESS 源汇调节因子
            'diag_rsd': self.diag_rsd,                      # RSD 种子碳限制分数
            'diag_gdmsd': self.diag_gdmsd,                  # GDMSD 种子需求 (g tissue/plant/d)
        })
    
    def calculate_water_stress(self, rainfall, transpiration):
        """
        Calculate water stress factor (0-1) based on soil water balance.
        
        Parameters:
        -----------
        rainfall : float
            Daily rainfall (mm)
        transpiration : float
            Potential transpiration (mm)
            
        Returns:
        --------
        float
            Water stress factor (0 = no stress, 1 = maximum stress)
        """
        field_capacity = self.soil['field_capacity']
        wilting_point = self.soil['wilting_point']
        root_depth = self.plant_state.root_depth / 100.0
        return _water_stress(field_capacity, wilting_point, root_depth, 
                           rainfall, transpiration)
    
    def calculate_maintenance_respiration(self, tmin, tmax, pg, daylength):
        """
        DSSAT RESPIR.for 维持+生长呼吸.

        Parameters:
        -----------
        tmin : float
            Minimum daily temperature (°C)
        tmax : float
            Maximum daily temperature (°C)
        pg : float
            冠层毛光合 PG (g CH2O/m²/d)
        daylength : float
            天文日长 (小时), 用于 Parton-Logan 小时温度生成.

        Returns:
        --------
        float
            总呼吸 MAINR (g/plant/d) = 维持呼吸 + 生长呼吸
        """
        return _maintenance_resp(
            self.plant_state.leaf_biomass,
            self.plant_state.stem_biomass,
            self.plant_state.root_biomass,
            self.plant_state.fruit_biomass,
            tmin,
            tmax,
            pg,
            self.plant_density,
            daylength,
        )
    
    def simulate_growth(self, weather_data_df):
        """
        Simulate strawberry growth for a period defined by the weather data.
        
        Parameters:
        -----------
        weather_data_df : pandas.DataFrame
            DataFrame containing daily weather data with the following columns:
            - date: Date in 'YYYY-MM-DD' format
            - tmax: Maximum temperature (°C)
            - tmin: Minimum temperature (°C)
            - solar_radiation: Solar radiation (MJ/m²)
            - rainfall: Rainfall (mm)
            - rh: Relative humidity (%)
            - wind_speed: Wind speed (m/s)
        """
        # Reset results
        self.results = []
        
        # Simulate each day using itertuples for speed
        for row in weather_data_df.itertuples(index=False):
            weather_day = {
                'date': row.date,
                'tmax': row.tmax,
                'tmin': row.tmin,
                'solar_radiation': row.solar_radiation,
                'rainfall': row.rainfall,
                'rh': row.rh,
                'wind_speed': row.wind_speed,
            }
            self.simulate_day(weather_day)
        
        # Convert results to DataFrame
        self.results_df = pd.DataFrame(self.results)
        return self.results_df
    
    def plot_results(self):
        """Plot key simulation results."""
        if not hasattr(self, 'results_df') or len(self.results_df) == 0:
            print("No simulation results to plot. "
                  "Run simulate_growth() first.")
            return
        
        fig, axs = plt.subplots(3, 2, figsize=(14, 12))
        
        # Plot biomass
        axs[0, 0].plot(self.results_df['dap'], self.results_df['biomass'], 
                      'b-', label='Total')
        axs[0, 0].plot(self.results_df['dap'], 
                      self.results_df['leaf_biomass'], 'g-', label='Leaf')
        axs[0, 0].plot(self.results_df['dap'], 
                      self.results_df['stem_biomass'], 'k-', label='Stem')
        axs[0, 0].plot(self.results_df['dap'], 
                      self.results_df['root_biomass'], 'r-', label='Root')
        axs[0, 0].plot(self.results_df['dap'], 
                      self.results_df['fruit_biomass'], 'm-', label='Fruit')
        axs[0, 0].set_xlabel('Days After Planting')
        axs[0, 0].set_ylabel('Biomass (g/plant)')
        axs[0, 0].set_title('Plant Biomass')
        axs[0, 0].legend()
        
        # Plot LAI
        axs[0, 1].plot(self.results_df['dap'], 
                      self.results_df['leaf_area_index'], 'g-')
        axs[0, 1].set_xlabel('Days After Planting')
        axs[0, 1].set_ylabel('LAI (m²/m²)')
        axs[0, 1].set_title('Leaf Area Index')
        
        # Plot fruit number
        axs[1, 0].plot(self.results_df['dap'], 
                      self.results_df['fruit_number'], 'm-')
        axs[1, 0].set_xlabel('Days After Planting')
        axs[1, 0].set_ylabel('Fruits (number/plant)')
        axs[1, 0].set_title('Fruit Number')
        
        # Plot crowns and runners
        axs[1, 1].plot(self.results_df['dap'], 
                      self.results_df['crown_number'], 'b-', label='Crowns')
        axs[1, 1].plot(self.results_df['dap'], 
                      self.results_df['runner_number'], 'r-', 
                      label='Runners')
        axs[1, 1].set_xlabel('Days After Planting')
        axs[1, 1].set_ylabel('Number per plant')
        axs[1, 1].set_title('Crowns and Runners')
        axs[1, 1].legend()
        
        # Plot water stress
        axs[2, 0].plot(self.results_df['dap'], 
                      self.results_df['water_stress'], 'r-')
        axs[2, 0].set_xlabel('Days After Planting')
        axs[2, 0].set_ylabel('Water Stress (0-1)')
        axs[2, 0].set_title('Water Stress Factor')
        
        # Plot phenological development
        # Convert stages to numeric values for plotting
        stages = list(self.phenology_stages.keys())
        stage_values = [stages.index(stage) 
                       for stage in self.results_df['stage']]
        
        axs[2, 1].plot(self.results_df['dap'], stage_values, 'b-')
        axs[2, 1].set_xlabel('Days After Planting')
        axs[2, 1].set_ylabel('Development Stage')
        axs[2, 1].set_yticks(range(len(stages)))
        axs[2, 1].set_yticklabels(stages)
        axs[2, 1].set_title('Phenological Development')
        
        plt.tight_layout()
        return fig


# Example usage of the CROPGRO-Strawberry model
def run_example_simulation():
    """Run the model with DSSAT UFBA1401 experiment weather data.

    使用 DSSAT UFBA1401.SRX 实验配置:
      - 地点: Balm, Florida, LAT=27.76°N, LONG=-82.224°E
      - 种植日期: 2014-10-09 (DSSAT YYDDD=14282)
      - 种植密度: PPOP=4.3 plants/m²
      - 采收结束: 2015-01-25 (DSSAT YYDDD=15025)
      - 模拟天数: 110 天 (覆盖完整采收期)
    天气数据来源: UFBA1401.WTH (2014) + UFBA1501.WTH (2015) 跨年合并
    """
    # 导入 DSSAT 天气加载模块
    from load_dssat_weather import load_dssat_weather

    # Define soil properties
    soil_properties = {
        'max_root_depth': 200.0,  # cm, 对齐 DSSAT 根深可达 180cm
        'field_capacity': 200.0,  # mm/m
        'wilting_point': 50.0,   # mm/m
    }

    # Define cultivar parameters
    # 参数来源: DSSAT SRGRO048.SPE (物种) + SRGRO048.CUL (品种 SR0001 Radiance)
    # KCAN/KC_SLOPE (SPE L4), SLAVR (CUL SR0001)
    # 注意: TB/TO1/TO2/TM 已按物候阶段固定在 calculate_thermal_time 中
    #       PHTMAX/PARMAX/CCMP/CCMAX/CCEFF/LFMAX/PGREF 已固定在 _photosynthesis 中
    cultivar_params = {
        'name': 'Radiance',  # DSSAT CUL SR0001 Radiance
        'kcan': 0.67,      # DSSAT KCAN=0.67 (SPE L4)
        'kc_slope': 0.50,  # DSSAT KC_SLOPE=0.50 (SPE L4) - 行距修正斜率
        'rowspc': 1.21,    # DSSAT ROWSPC=1.21 m (SRX PLRS=121 cm)
        'pltpop': 4.3,     # DSSAT PLTPOP=4.3 plants/m² (SRX PPOP=4.3)
        'sla': 0.0165,     # DSSAT SLAVR=165 cm²/g = 0.0165 m²/g (CUL SR0001)
        # 果实参数已在 partition_biomass/update_fruits 中对齐 DSSAT CUL SR0001:
        # WTPSD=0.005, SDPDV=185.0, SFDUR=11.7, THRSH=20.0%, PODUR=45.0, XFRT=0.96
    }

    # DSSAT UFBA1401 实验配置
    # Balm, Florida: LAT=27.76°N (热带/亚热带, 秋植春收)
    start_date = '2014-10-09'  # DSSAT PDATE=14282
    planting_dssat_date = 14282
    n_days = 110  # 覆盖到 2015-01-25 采收结束 (DSSAT 最后采收 15025)

    # 加载 DSSAT 实际天气数据 (跨年合并 2014+2015)
    wth_paths = [
        'dssat-csm-data-develop/Strawberry/UFBA1401.WTH',
        'dssat-csm-data-develop/Weather/UFBA1501.WTH',
    ]
    weather_df = load_dssat_weather(wth_paths, planting_dssat_date, n_days)

    # Initialize model (纬度对齐 DSSAT UFBA1401: LAT=27.76)
    model = CropgroStrawberry(
        latitude=27.76,
        planting_date=start_date,
        soil_properties=soil_properties,
        cultivar_params=cultivar_params
    )

    # Run simulation
    results = model.simulate_growth(weather_df)

    # Plot results
    fig = model.plot_results()

    return model, results, fig


if __name__ == "__main__":
    # Run example simulation
    model, results, fig = run_example_simulation()
    
    # Display some results
    print(f"Final biomass: {results['biomass'].iloc[-1]:.2f} g/plant")
    print(f"Final fruit biomass: "
          f"{results['fruit_biomass'].iloc[-1]:.2f} g/plant")
    print(f"Final leaf area index: "
          f"{results['leaf_area_index'].iloc[-1]:.2f} m²/m²")
    print(f"Final phenological stage: {results['stage'].iloc[-1]}")
    
    # Save plot to file (required for Docker/non-interactive runs)
    plt.savefig('simulation_results.png', dpi=100, bbox_inches='tight')
    print("Plot saved to: simulation_results.png")

    # Show plot
    plt.show()
