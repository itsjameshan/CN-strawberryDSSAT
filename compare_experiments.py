import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

# 读取数据
df = pd.read_csv('all_experiments_daily_data.csv')
# 只选取14、16、17年实验
exp_ids = ['UFBA1401', 'UFBA1601', 'UFBA1701']
colors = {'UFBA1401': 'royalblue', 'UFBA1601': 'firebrick', 'UFBA1701': 'green'}

# 创建2行2列的子图
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=("生物量随天数变化", "叶面积指数随天数变化", "根系深度随天数变化", "光合速率随天数变化")
)

# 依次添加三组实验曲线
for exp in exp_ids:
    dfe = df[df['experiment'] == exp]
    fig.add_trace(
        go.Scatter(
            x=dfe['dap'], y=dfe['biomass'],
            mode='lines+markers',
            name=f'{exp} 生物量',
            line=dict(color=colors[exp]),
            legendgroup=exp,
            showlegend=True
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=dfe['dap'], y=dfe['leaf_area_index'],
            mode='lines+markers',
            name=f'{exp} 叶面积指数',
            line=dict(color=colors[exp]),
            legendgroup=exp,
            showlegend=False
        ),
        row=1, col=2
    )
    fig.add_trace(
        go.Scatter(
            x=dfe['dap'], y=dfe['root_depth'],
            mode='lines+markers',
            name=f'{exp} 根系深度',
            line=dict(color=colors[exp]),
            legendgroup=exp,
            showlegend=False
        ),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=dfe['dap'], y=dfe['photosynthesis'],
            mode='lines+markers',
            name=f'{exp} 光合速率',
            line=dict(color=colors[exp]),
            legendgroup=exp,
            showlegend=False
        ),
        row=2, col=2
    )

fig.update_layout(
    title="UFBA1401/1601/1701 草莓生长关键指标对比图",
    height=800,
    width=1000,
    legend_title="实验编号",
    legend=dict(itemsizing='constant')
)
fig.update_xaxes(title_text="天数", row=1, col=1)
fig.update_xaxes(title_text="天数", row=1, col=2)
fig.update_xaxes(title_text="天数", row=2, col=1)
fig.update_xaxes(title_text="天数", row=2, col=2)
fig.update_yaxes(title_text="生物量", row=1, col=1)
fig.update_yaxes(title_text="叶面积指数", row=1, col=2)
fig.update_yaxes(title_text="根系深度", row=2, col=1)
fig.update_yaxes(title_text="光合速率", row=2, col=2)

fig.write_html("compare_experiments.html")
print("对比图已保存为 compare_experiments.html")
fig.show() 