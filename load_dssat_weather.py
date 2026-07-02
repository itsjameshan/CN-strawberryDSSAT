# -*- coding: utf-8 -*-
"""
加载 DSSAT UFBA1401 实验天气数据, 用于 Python 模型.

DSSAT 天气文件格式:
    @DATE  SRAD  TMAX  TMIN  RAIN  DEWP  WIND   PAR  EVAP  RHUM
    14282  20.0  31.2  19.5   0.0  20.8  236.4              80.0

日期格式: YYDDD (年后2位 + 儒略日)
    14282 = 2014年第282天 = 2014-10-09

单位换算:
    SRAD: MJ/m²/d (与 Python 一致)
    TMAX/TMIN: °C (与 Python 一致)
    RAIN: mm (与 Python 一致)
    WIND: km/d → m/s (÷86.4)
    RHUM: % (与 Python 一致)
"""

import pandas as pd
from datetime import datetime, timedelta


def dssat_date_to_calendar(dssat_date):
    """将 DSSAT 日期 (YYDDD) 转换为日历日期.

    Parameters:
        dssat_date (int): DSSAT 日期, 如 14282 = 2014年第282天

    Returns:
        str: 日历日期 'YYYY-MM-DD'
    """
    year = 2000 + int(str(dssat_date)[:2]) if int(str(dssat_date)[:2]) < 50 \
        else 1900 + int(str(dssat_date)[:2])
    doy = int(str(dssat_date)[2:])
    base = datetime(year, 1, 1) + timedelta(days=doy - 1)
    return base.strftime('%Y-%m-%d')


def _parse_wth_file(wth_path):
    """解析单个 DSSAT .WTH 文件, 返回日期记录列表.

    Parameters:
        wth_path (str): DSSAT .WTH 文件路径

    Returns:
        list[dict]: 天气记录列表, 每条含 dssat_date 和天气要素
    """
    with open(wth_path, 'r') as f:
        lines = f.readlines()

    # 找到 @DATE 行
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith('@DATE'):
            header_idx = i
            break

    if header_idx is None:
        raise ValueError(f"无法在 {wth_path} 中找到 @DATE 头部行")

    records = []
    for line in lines[header_idx + 1:]:
        parts = line.split()
        if len(parts) < 7:
            continue
        try:
            dssat_date = int(parts[0])
            srad = float(parts[1])
            tmax = float(parts[2])
            tmin = float(parts[3])
            rain = float(parts[4])
            wind_kmd = float(parts[6])
            rhum = float(parts[8]) if len(parts) > 8 and parts[8] != '' else 70.0

            wind_ms = wind_kmd / 86.4  # km/d → m/s
            date_str = dssat_date_to_calendar(dssat_date)

            records.append({
                'dssat_date': dssat_date,
                'date': date_str,
                'tmax': tmax,
                'tmin': tmin,
                'solar_radiation': srad,
                'rainfall': rain,
                'rh': rhum,
                'wind_speed': wind_ms
            })
        except (ValueError, IndexError):
            continue

    return records


def load_dssat_weather(wth_path, planting_dssat_date, n_days):
    """加载 DSSAT 天气文件, 从种植日期开始提取 n_days 天.

    Parameters:
        wth_path (str or list[str]): DSSAT .WTH 文件路径, 或跨年文件路径列表
        planting_dssat_date (int): 种植日期 (YYDDD 格式), 如 14282
        n_days (int): 提取的天数

    Returns:
        pd.DataFrame: 天气数据, 列名与 Python 模型一致:
            date, tmax, tmin, solar_radiation, rainfall, rh, wind_speed
    """
    # 支持单文件或跨年多文件合并
    if isinstance(wth_path, (list, tuple)):
        all_records = []
        for p in wth_path:
            all_records.extend(_parse_wth_file(p))
        df = pd.DataFrame(all_records)
        # 按 dssat_date 排序去重 (跨年合并可能重复)
        df = df.drop_duplicates(subset='dssat_date').sort_values('dssat_date').reset_index(drop=True)
    else:
        records = _parse_wth_file(wth_path)
        df = pd.DataFrame(records)

    # 从种植日期开始提取
    plant_idx = df[df['dssat_date'] == planting_dssat_date].index
    if len(plant_idx) == 0:
        raise ValueError(f"种植日期 {planting_dssat_date} 不在天气文件中")

    start_idx = plant_idx[0]
    end_idx = min(start_idx + n_days, len(df))
    result = df.iloc[start_idx:end_idx].reset_index(drop=True)

    # 移除临时列
    result = result.drop(columns=['dssat_date'])

    print(f"加载 DSSAT 天气数据: {wth_path}")
    print(f"  种植日期: {planting_dssat_date} ({result['date'].iloc[0]})")
    print(f"  提取天数: {len(result)}")
    print(f"  日期范围: {result['date'].iloc[0]} ~ {result['date'].iloc[-1]}")
    print(f"  温度范围: tmax={result['tmax'].min():.1f}~{result['tmax'].max():.1f}°C, "
          f"tmin={result['tmin'].min():.1f}~{result['tmin'].max():.1f}°C")
    print(f"  辐射范围: {result['solar_radiation'].min():.1f}~{result['solar_radiation'].max():.1f} MJ/m²/d")
    print(f"  风速范围: {result['wind_speed'].min():.2f}~{result['wind_speed'].max():.2f} m/s")

    return result


if __name__ == '__main__':
    # 测试跨年合并加载 (2014 + 2015 天气数据)
    # UFBA1401.WTH: 2014年数据 (种植日 14282 = 2014-10-09)
    # UFBA1501.WTH: 2015年数据 (覆盖到采收结束 15077 = 2015-03-18)
    # 天气文件内置在仓库 weather/ 目录
    wth_paths = [
        'weather/UFBA1401.WTH',
        'weather/UFBA1501.WTH',
    ]
    planting_date = 14282  # 2014-10-09
    n_days = 110  # 模拟 110 天 (覆盖到 2015-01-25 采收结束)

    weather = load_dssat_weather(wth_paths, planting_date, n_days)
    print(f"\n前5天天气数据:")
    print(weather.head())
    print(f"\n后5天天气数据:")
    print(weather.tail())
