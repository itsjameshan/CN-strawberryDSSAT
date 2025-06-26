import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline as pyo

# 读取数据
df = pd.read_csv('weather_data.csv')
df['date'] = pd.to_datetime(df['date'])

# 添加月份和季节信息
df['month'] = df['date'].dt.month
df['season'] = df['date'].dt.month.map({12: '冬季', 1: '冬季', 2: '冬季',
                                        3: '春季', 4: '春季', 5: '春季',
                                        6: '夏季', 7: '夏季', 8: '夏季',
                                        9: '秋季', 10: '秋季', 11: '秋季'})

print("数据加载完成，开始生成动态图表...")

# 1. 气温变化动态折线图
def create_temperature_animation():
    """创建气温变化动态图"""
    fig = px.line(df, x='date', y=['tmax', 'tmin'], 
                  title='2092年气温变化动态图',
                  labels={'value': '温度 (°C)', 'date': '日期', 'variable': '温度类型'},
                  color_discrete_map={'tmax': 'red', 'tmin': 'blue'})
    
    fig.update_layout(
        title_x=0.5,
        xaxis_title="日期",
        yaxis_title="温度 (°C)",
        hovermode='x unified'
    )
    
    # 添加动画帧
    frames = []
    for i in range(0, len(df), 7):  # 每周一帧
        frame_data = df.iloc[:i+1]
        frame = go.Frame(
            data=[
                go.Scatter(x=frame_data['date'], y=frame_data['tmax'], 
                          mode='lines', name='最高气温', line=dict(color='red')),
                go.Scatter(x=frame_data['date'], y=frame_data['tmin'], 
                          mode='lines', name='最低气温', line=dict(color='blue'))
            ],
            name=f'frame_{i}'
        )
        frames.append(frame)
    
    fig.frames = frames
    
    # 添加播放按钮
    fig.update_layout(
        updatemenus=[{
            'type': 'buttons',
            'showactive': False,
            'buttons': [
                {
                    'label': '播放',
                    'method': 'animate',
                    'args': [None, {'frame': {'duration': 100, 'redraw': True}, 
                                   'fromcurrent': True, 'transition': {'duration': 50}}]
                },
                {
                    'label': '暂停',
                    'method': 'animate',
                    'args': [[None], {'frame': {'duration': 0, 'redraw': False}, 
                                     'mode': 'immediate', 'transition': {'duration': 0}}]
                }
            ]
        }]
    )
    
    fig.write_html('temperature_animation.html')
    print("气温动态图已保存为 temperature_animation.html")
    return fig

# 2. 降水量动态柱状图
def create_rainfall_animation():
    """创建降水量动态柱状图"""
    fig = px.bar(df, x='date', y='rainfall', 
                 title='2092年降水量变化动态图',
                 labels={'rainfall': '降水量 (mm)', 'date': '日期'},
                 color='rainfall',
                 color_continuous_scale='Blues')
    
    fig.update_layout(
        title_x=0.5,
        xaxis_title="日期",
        yaxis_title="降水量 (mm)",
        coloraxis_colorbar_title="降水量 (mm)"
    )
    
    # 添加动画帧
    frames = []
    for i in range(0, len(df), 5):  # 每5天一帧
        frame_data = df.iloc[:i+1]
        frame = go.Frame(
            data=[
                go.Bar(x=frame_data['date'], y=frame_data['rainfall'],
                      marker_color=frame_data['rainfall'],
                      marker_colorscale='Blues')
            ],
            name=f'frame_{i}'
        )
        frames.append(frame)
    
    fig.frames = frames
    
    # 添加播放按钮
    fig.update_layout(
        updatemenus=[{
            'type': 'buttons',
            'showactive': False,
            'buttons': [
                {
                    'label': '播放',
                    'method': 'animate',
                    'args': [None, {'frame': {'duration': 80, 'redraw': True}, 
                                   'fromcurrent': True, 'transition': {'duration': 40}}]
                },
                {
                    'label': '暂停',
                    'method': 'animate',
                    'args': [[None], {'frame': {'duration': 0, 'redraw': False}, 
                                     'mode': 'immediate', 'transition': {'duration': 0}}]
                }
            ]
        }]
    )
    
    fig.write_html('rainfall_animation.html')
    print("降水量动态图已保存为 rainfall_animation.html")
    return fig

# 3. 太阳辐射动态面积图
def create_solar_radiation_animation():
    """创建太阳辐射动态面积图"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['solar_radiation'],
        fill='tonexty',
        fillcolor='rgba(255, 165, 0, 0.3)',
        line=dict(color='orange', width=2),
        name='太阳辐射'
    ))
    
    fig.update_layout(
        title='2092年太阳辐射变化动态图',
        title_x=0.5,
        xaxis_title="日期",
        yaxis_title="太阳辐射",
        showlegend=True
    )
    
    # 添加动画帧
    frames = []
    for i in range(0, len(df), 7):  # 每周一帧
        frame_data = df.iloc[:i+1]
        frame = go.Frame(
            data=[
                go.Scatter(
                    x=frame_data['date'], y=frame_data['solar_radiation'],
                    fill='tonexty',
                    fillcolor='rgba(255, 165, 0, 0.3)',
                    line=dict(color='orange', width=2),
                    name='太阳辐射'
                )
            ],
            name=f'frame_{i}'
        )
        frames.append(frame)
    
    fig.frames = frames
    
    # 添加播放按钮
    fig.update_layout(
        updatemenus=[{
            'type': 'buttons',
            'showactive': False,
            'buttons': [
                {
                    'label': '播放',
                    'method': 'animate',
                    'args': [None, {'frame': {'duration': 100, 'redraw': True}, 
                                   'fromcurrent': True, 'transition': {'duration': 50}}]
                },
                {
                    'label': '暂停',
                    'method': 'animate',
                    'args': [[None], {'frame': {'duration': 0, 'redraw': False}, 
                                     'mode': 'immediate', 'transition': {'duration': 0}}]
                }
            ]
        }]
    )
    
    fig.write_html('solar_radiation_animation.html')
    print("太阳辐射动态图已保存为 solar_radiation_animation.html")
    return fig

# 4. 多变量综合动态图
def create_multi_variable_animation():
    """创建多变量综合动态图"""
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('气温变化', '降水量', '太阳辐射'),
        vertical_spacing=0.1
    )
    
    # 添加初始数据
    fig.add_trace(go.Scatter(x=df['date'], y=df['tmax'], name='最高气温', 
                            line=dict(color='red')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['date'], y=df['tmin'], name='最低气温', 
                            line=dict(color='blue')), row=1, col=1)
    fig.add_trace(go.Bar(x=df['date'], y=df['rainfall'], name='降水量', 
                        marker_color='lightblue'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df['date'], y=df['solar_radiation'], name='太阳辐射', 
                            line=dict(color='orange')), row=3, col=1)
    
    fig.update_layout(
        title='2092年气象要素综合动态图',
        title_x=0.5,
        height=800,
        showlegend=True
    )
    
    # 添加动画帧
    frames = []
    for i in range(0, len(df), 10):  # 每10天一帧
        frame_data = df.iloc[:i+1]
        frame = go.Frame(
            data=[
                go.Scatter(x=frame_data['date'], y=frame_data['tmax'], 
                          line=dict(color='red')),  # 最高气温
                go.Scatter(x=frame_data['date'], y=frame_data['tmin'], 
                          line=dict(color='blue')),  # 最低气温
                go.Bar(x=frame_data['date'], y=frame_data['rainfall'], 
                      marker_color='lightblue'),  # 降水量
                go.Scatter(x=frame_data['date'], y=frame_data['solar_radiation'], 
                          line=dict(color='orange'))  # 太阳辐射
            ],
            name=f'frame_{i}'
        )
        frames.append(frame)
    
    fig.frames = frames
    
    # 添加播放按钮
    fig.update_layout(
        updatemenus=[{
            'type': 'buttons',
            'showactive': False,
            'buttons': [
                {
                    'label': '播放',
                    'method': 'animate',
                    'args': [None, {'frame': {'duration': 120, 'redraw': True}, 
                                   'fromcurrent': True, 'transition': {'duration': 60}}]
                },
                {
                    'label': '暂停',
                    'method': 'animate',
                    'args': [[None], {'frame': {'duration': 0, 'redraw': False}, 
                                     'mode': 'immediate', 'transition': {'duration': 0}}]
                }
            ]
        }]
    )
    
    fig.write_html('multi_variable_animation.html')
    print("多变量综合动态图已保存为 multi_variable_animation.html")
    return fig

# 5. 气泡图：气温vs太阳辐射，气泡大小为降水量
def create_bubble_animation():
    """创建气泡动态图"""
    fig = px.scatter(df, x='tmax', y='solar_radiation', 
                     size='rainfall', color='month',
                     title='气温-太阳辐射-降水量关系动态图',
                     labels={'tmax': '最高气温 (°C)', 'solar_radiation': '太阳辐射', 
                            'rainfall': '降水量 (mm)', 'month': '月份'},
                     color_continuous_scale='viridis',
                     size_max=30)
    
    fig.update_layout(
        title_x=0.5,
        xaxis_title="最高气温 (°C)",
        yaxis_title="太阳辐射"
    )
    
    # 添加动画帧
    frames = []
    for i in range(0, len(df), 5):  # 每5天一帧
        frame_data = df.iloc[:i+1]
        frame = go.Frame(
            data=[
                go.Scatter(
                    x=frame_data['tmax'], y=frame_data['solar_radiation'],
                    mode='markers',
                    marker=dict(
                        size=frame_data['rainfall'] * 2,  # 气泡大小
                        color=frame_data['month'],
                        colorscale='viridis',
                        showscale=True,
                        colorbar=dict(title="月份")
                    ),
                    text=frame_data['date'].dt.strftime('%Y-%m-%d'),
                    hovertemplate='<b>日期</b>: %{text}<br>' +
                                '<b>最高气温</b>: %{x}°C<br>' +
                                '<b>太阳辐射</b>: %{y}<br>' +
                                '<b>降水量</b>: %{marker.size/2:.1f}mm<extra></extra>'
                )
            ],
            name=f'frame_{i}'
        )
        frames.append(frame)
    
    fig.frames = frames
    
    # 添加播放按钮
    fig.update_layout(
        updatemenus=[{
            'type': 'buttons',
            'showactive': False,
            'buttons': [
                {
                    'label': '播放',
                    'method': 'animate',
                    'args': [None, {'frame': {'duration': 80, 'redraw': True}, 
                                   'fromcurrent': True, 'transition': {'duration': 40}}]
                },
                {
                    'label': '暂停',
                    'method': 'animate',
                    'args': [[None], {'frame': {'duration': 0, 'redraw': False}, 
                                     'mode': 'immediate', 'transition': {'duration': 0}}]
                }
            ]
        }]
    )
    
    fig.write_html('bubble_animation.html')
    print("气泡动态图已保存为 bubble_animation.html")
    return fig

# 6. 年度气象热力图
def create_heatmap():
    """创建年度气象热力图"""
    # 准备热力图数据
    df_heatmap = df.copy()
    df_heatmap['day_of_year'] = df_heatmap['date'].dt.dayofyear
    df_heatmap['month'] = df_heatmap['date'].dt.month
    
    # 创建气温热力图
    fig_temp = px.imshow(
        df_heatmap.pivot(index='month', columns='day_of_year', values='tmax'),
        title='2092年最高气温热力图',
        labels=dict(x="一年中的第几天", y="月份", color="温度 (°C)"),
        color_continuous_scale='Reds',
        aspect='auto'
    )
    
    fig_temp.update_layout(
        title_x=0.5,
        xaxis_title="一年中的第几天",
        yaxis_title="月份"
    )
    
    fig_temp.write_html('temperature_heatmap.html')
    print("气温热力图已保存为 temperature_heatmap.html")
    
    # 创建降水量热力图
    fig_rain = px.imshow(
        df_heatmap.pivot(index='month', columns='day_of_year', values='rainfall'),
        title='2092年降水量热力图',
        labels=dict(x="一年中的第几天", y="月份", color="降水量 (mm)"),
        color_continuous_scale='Blues',
        aspect='auto'
    )
    
    fig_rain.update_layout(
        title_x=0.5,
        xaxis_title="一年中的第几天",
        yaxis_title="月份"
    )
    
    fig_rain.write_html('rainfall_heatmap.html')
    print("降水量热力图已保存为 rainfall_heatmap.html")
    
    return fig_temp, fig_rain

# 主函数
def main():
    """生成所有动态图表"""
    print("开始生成动态气象图表...")
    
    try:
        # 生成各种动态图
        create_temperature_animation()
        create_rainfall_animation()
        create_solar_radiation_animation()
        create_multi_variable_animation()
        create_bubble_animation()
        create_heatmap()
        
        print("\n所有图表生成完成！")
        print("生成的文件包括：")
        print("- temperature_animation.html (气温动态图)")
        print("- rainfall_animation.html (降水量动态图)")
        print("- solar_radiation_animation.html (太阳辐射动态图)")
        print("- multi_variable_animation.html (多变量综合动态图)")
        print("- bubble_animation.html (气泡动态图)")
        print("- temperature_heatmap.html (气温热力图)")
        print("- rainfall_heatmap.html (降水量热力图)")
        
    except Exception as e:
        print(f"生成图表时出错: {e}")

if __name__ == "__main__":
    main() 