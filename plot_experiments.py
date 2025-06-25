import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

# 读取数据
df = pd.read_csv('all_experiments_daily_data.csv')
# 获取所有实验编号
experiments = df['experiment'].unique()

# 创建2行2列的子图
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=("生物量随天数变化", "叶面积指数随天数变化", "根系深度随天数变化", "光合速率随天数变化")
)

# 只显示第一个实验的初始帧
exp0 = experiments[0]
df0 = df[df['experiment'] == exp0]
fig.add_trace(go.Scatter(x=[df0['dap'].iloc[0]], y=[df0['biomass'].iloc[0]], mode='lines+markers', name='生物量 (biomass)'), row=1, col=1)
fig.add_trace(go.Scatter(x=[df0['dap'].iloc[0]], y=[df0['leaf_area_index'].iloc[0]], mode='lines+markers', name='叶面积指数 (LAI)', marker=dict(color='green')), row=1, col=2)
fig.add_trace(go.Scatter(x=[df0['dap'].iloc[0]], y=[df0['root_depth'].iloc[0]], mode='lines+markers', name='根系深度 (root_depth)', marker=dict(color='orange')), row=2, col=1)
fig.add_trace(go.Scatter(x=[df0['dap'].iloc[0]], y=[df0['photosynthesis'].iloc[0]], mode='lines+markers', name='光合速率 (photosynthesis)', marker=dict(color='purple')), row=2, col=2)
# 动画帧
frames = []
for exp in experiments:
    dfe = df[df['experiment'] == exp].reset_index(drop=True)
    for k in range(1, len(dfe)):
        frames.append(go.Frame(
            data=[
                go.Scatter(x=dfe['dap'][:k+1], y=dfe['biomass'][:k+1], mode='lines+markers'),
                go.Scatter(x=dfe['dap'][:k+1], y=dfe['leaf_area_index'][:k+1], mode='lines+markers', marker=dict(color='green')),
                go.Scatter(x=dfe['dap'][:k+1], y=dfe['root_depth'][:k+1], mode='lines+markers', marker=dict(color='orange')),
                go.Scatter(x=dfe['dap'][:k+1], y=dfe['photosynthesis'][:k+1], mode='lines+markers', marker=dict(color='purple')),
            ],
            name=f"{exp}_{k}",
            traces=[0, 1, 2, 3]
        ))
# 设置下拉菜单用于切换实验
updatemenus = [
    dict(
        buttons=[
            dict(
                label=str(exp),
                method="animate",
                args=[
                    [f"{exp}_{k}" for k in range(1, len(df[df['experiment'] == exp]))],
                    {"frame": {"duration": 1, "redraw": True}, "fromcurrent": True}
                ]
            ) for exp in experiments
        ],
        direction="down",
        showactive=True,
        x=0.1,
        y=1.15,
        xanchor="left",
        yanchor="top"
    )
]

# 设置动画按钮
fig.update_layout(
    title_text="多实验草莓生长模拟关键指标动态图（可切换实验+动画）",
    showlegend=False,
    height=800,
    width=1000,
    updatemenus=updatemenus
)

# 添加动画帧
fig.frames = frames

# 显示图表
print("准备保存html文件")
fig.write_html("mytest_animation.html")
print("保存完成")
fig.show()