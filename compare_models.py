# -*- coding: utf-8 -*-
"""DSSAT vs Python 模型对比图.

读取 DSSAT PlantGro.OUT 和 Python 模型每日输出, 生成对比图.
单位换算: DSSAT kg/ha -> g/plant (÷43), LAID 保持 m²/m², G#AD 保持 no./m².
"""
import importlib.util
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

# ============================================================
# 1. 读取 DSSAT PlantGro.OUT
# ============================================================
def load_dssat_results(path='dssat_results/PlantGro.OUT'):
    """解析 DSSAT PlantGro.OUT, 返回 DataFrame."""
    rows = []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith('@') or not line.strip():
                continue
            parts = line.split()
            if len(parts) < 15:
                continue
            try:
                dap = int(parts[3])
            except ValueError:
                continue
            lnsd = float(parts[4])
            lai = float(parts[6])
            lwad = float(parts[7])   # leaf kg/ha
            swad = float(parts[8])   # stem kg/ha
            gwad = float(parts[9])   # seed kg/ha
            rwad = float(parts[10])  # root kg/ha
            cwad = float(parts[12])  # canopy kg/ha
            gnad = float(parts[13])  # grain #/m²
            pwad = float(parts[15]) if len(parts) > 15 else 0.0  # pod/shell kg/ha
            rows.append({
                'dap': dap,
                'vstage_dssat': lnsd,
                'lai_dssat': lai,
                'leaf_dssat': lwad / 43.0,    # g/plant
                'stem_dssat': swad / 43.0,
                'root_dssat': rwad / 43.0,
                'fruit_dssat': (gwad + pwad) / 43.0,
                'total_dssat': cwad / 43.0,
                'fruitnum_dssat': gnad,
            })
    return pd.DataFrame(rows)

# ============================================================
# 2. 运行 Python 模型
# ============================================================
def run_python_model():
    """运行 Python 模型, 返回每日 DataFrame."""
    spec = importlib.util.spec_from_file_location(
        "model", "cropgro-strawberry-implementation.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    model, results, fig = mod.run_example_simulation()
    return results

# ============================================================
# 3. 生成对比图
# ============================================================
def make_comparison_plot(dssat_df, py_df, savepath='model_comparison.png'):
    """生成 DSSAT vs Python 对比图 (2x4 子图)."""
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    fig.suptitle('DSSAT vs Python CROPGRO-Strawberry 模型对比 (UFBA1401 SR0001 Radiance)',
                 fontsize=16, fontweight='bold')

    plot_configs = [
        ('总生物量', 'biomass',       'total_dssat',  '(g/plant)', axes[0, 0]),
        ('叶片生物量', 'leaf_biomass', 'leaf_dssat',  '(g/plant)', axes[0, 1]),
        ('茎生物量',   'stem_biomass', 'stem_dssat',  '(g/plant)', axes[0, 2]),
        ('根生物量',   'root_biomass', 'root_dssat',  '(g/plant)', axes[0, 3]),
        ('LAI 叶面积指数', 'leaf_area_index', 'lai_dssat', '(m²/m²)',  axes[1, 0]),
        ('果实生物量', 'fruit_biomass','fruit_dssat', '(g/plant)', axes[1, 1]),
        ('果实数量',  'fruit_number', 'fruitnum_dssat', '(no./m²)', axes[1, 2]),
        ('V-stage 叶数', 'vstage',    'vstage_dssat', '(leaves)',  axes[1, 3]),
    ]

    for title, py_col, dssat_col, unit, ax in plot_configs:
        ax.plot(dssat_df['dap'], dssat_df[dssat_col],
                'b-o', markersize=3, label='DSSAT', linewidth=1.5)
        if py_col in py_df.columns:
            ax.plot(py_df['dap'], py_df[py_col], 'r-s', markersize=3,
                    label='Python', linewidth=1.5)
        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.set_xlabel('DAP (移栽后天数)', fontsize=11)
        ax.set_ylabel(f'{title} {unit}', fontsize=11)
        ax.legend(fontsize=10, loc='upper left')
        ax.grid(True, alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(savepath, dpi=150, bbox_inches='tight')
    print(f"对比图已保存: {savepath}")
    plt.show()

# ============================================================
# 4. 数值对比表
# ============================================================
def print_comparison_table(dssat_df, py_df):
    """打印关键 DAP 的数值对比表."""
    print("\n" + "=" * 120)
    print("DSSAT vs Python 关键 DAP 数值对比")
    print("=" * 120)
    print(f"{'DAP':>4} | {'变量':>12} | {'DSSAT':>10} | {'Python':>10} | {'差异':>10} | {'相对误差%':>10}")
    print("-" * 120)

    check_daps = [0, 10, 20, 30, 40, 50, 60, 70, 80, 84]
    variables = [
        ('total',   '总生物量',   'biomass',       'total_dssat'),
        ('leaf',    '叶片生物量', 'leaf_biomass',  'leaf_dssat'),
        ('stem',    '茎生物量',   'stem_biomass', 'stem_dssat'),
        ('root',    '根生物量',   'root_biomass', 'root_dssat'),
        ('fruit',   '果实生物量', 'fruit_biomass','fruit_dssat'),
        ('lai',     'LAI',       'leaf_area_index','lai_dssat'),
        ('fruitnum','果实数量',   'fruit_number', 'fruitnum_dssat'),
    ]

    for dap in check_daps:
        dssat_row = dssat_df[dssat_df['dap'] == dap]
        py_row = py_df[py_df['dap'] == dap]
        if dssat_row.empty or py_row.empty:
            continue
        d = dssat_row.iloc[0]
        p = py_row.iloc[0]
        for _, label, py_col, dssat_col in variables:
            dval = d[dssat_col]
            pval = p[py_col]
            diff = pval - dval
            rel_err = (diff / dval * 100) if abs(dval) > 1e-6 else float('inf')
            print(f"{dap:4d} | {label:>12} | {dval:10.3f} | {pval:10.3f} | {diff:+10.3f} | {rel_err:+10.1f}%")
        print("-" * 120)

# ============================================================
# 主程序
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("DSSAT vs Python 草莓模型对比")
    print("=" * 60)

    print("\n[1/3] 读取 DSSAT PlantGro.OUT ...")
    dssat_df = load_dssat_results()
    print(f"  DSSAT 数据: {len(dssat_df)} 天, DAP {dssat_df['dap'].min()}-{dssat_df['dap'].max()}")

    print("\n[2/3] 运行 Python 模型 ...")
    py_df = run_python_model()
    print(f"  Python 数据: {len(py_df)} 天, DAP {int(py_df['dap'].min())}-{int(py_df['dap'].max())}")

    print("\n[3/3] 生成对比图 ...")
    make_comparison_plot(dssat_df, py_df)

    print_comparison_table(dssat_df, py_df)
