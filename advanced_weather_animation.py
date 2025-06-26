import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 读取数据
print("正在读取数据...")
df = pd.read_csv('weather_data.csv')
df['date'] = pd.to_datetime(df['date'])

# 处理缺失值（-99.0）
df['tmax_clean'] = df['tmax'].replace(-99.0, df['tmax'].median())
df['tmin_clean'] = df['tmin'].replace(-99.0, df['tmin'].median())

print(f"数据加载完成，共 {len(df)} 条记录")

def create_advanced_temperature_animation():
    """创建高级气温动态图，带时间轴滑块"""
    print("正在生成高级气温动态图...")
    
    fig = go.Figure()
    
    # 添加最高气温线
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['tmax_clean'],
        mode='lines+markers',
        name='最高气温',
        line=dict(color='red', width=2),
        marker=dict(size=4, color='red'),
        hovertemplate='<b>日期</b>: %{x}<br>' +
                     '<b>最高气温</b>: %{y:.1f}°C<extra></extra>'
    ))
    
    # 添加最低气温线
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['tmin_clean'],
        mode='lines+markers',
        name='最低气温',
        line=dict(color='blue', width=2),
        marker=dict(size=4, color='blue'),
        hovertemplate='<b>日期</b>: %{x}<br>' +
                     '<b>最低气温</b>: %{y:.1f}°C<extra></extra>'
    ))
    
    # 添加温度范围填充
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['tmax_clean'],
        mode='lines',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['tmin_clean'],
        mode='lines',
        line=dict(width=0),
        fill='tonexty',
        fillcolor='rgba(255, 0, 0, 0.1)',
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # 更新布局
    fig.update_layout(
        title='2092年气温变化动态图（带时间轴滑块）',
        title_x=0.5,
        xaxis_title="日期",
        yaxis_title="温度 (°C)",
        hovermode='x unified',
        height=600,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # 添加时间轴滑块
    fig.update_layout(
        xaxis=dict(
            rangeslider=dict(visible=True),
            type="date"
        )
    )
    
    # 添加动画帧
    frames = []
    step = max(1, len(df) // 50)  # 50帧动画
    
    for i in range(0, len(df), step):
        frame_data = df.iloc[:i+1]
        frame = go.Frame(
            data=[
                go.Scatter(x=frame_data['date'], y=frame_data['tmax_clean'],
                          mode='lines+markers', name='最高气温',
                          line=dict(color='red', width=2),
                          marker=dict(size=4, color='red')),
                go.Scatter(x=frame_data['date'], y=frame_data['tmin_clean'],
                          mode='lines+markers', name='最低气温',
                          line=dict(color='blue', width=2),
                          marker=dict(size=4, color='blue')),
                go.Scatter(x=frame_data['date'], y=frame_data['tmax_clean'],
                          mode='lines', line=dict(width=0), showlegend=False),
                go.Scatter(x=frame_data['date'], y=frame_data['tmin_clean'],
                          mode='lines', line=dict(width=0), fill='tonexty',
                          fillcolor='rgba(255, 0, 0, 0.1)', showlegend=False)
            ],
            name=f'frame_{i}'
        )
        frames.append(frame)
    
    fig.frames = frames
    
    # 添加播放控制按钮
    fig.update_layout(
        updatemenus=[{
            'type': 'buttons',
            'showactive': False,
            'buttons': [
                {
                    'label': '▶ 播放',
                    'method': 'animate',
                    'args': [None, {
                        'frame': {'duration': 100, 'redraw': True},
                        'fromcurrent': True,
                        'transition': {'duration': 50}
                    }]
                },
                {
                    'label': '⏸ 暂停',
                    'method': 'animate',
                    'args': [[None], {
                        'frame': {'duration': 0, 'redraw': False},
                        'mode': 'immediate',
                        'transition': {'duration': 0}
                    }]
                },
                {
                    'label': '⏮ 重置',
                    'method': 'animate',
                    'args': [[0], {
                        'frame': {'duration': 0, 'redraw': True},
                        'mode': 'immediate',
                        'transition': {'duration': 0}
                    }]
                }
            ],
            'direction': 'left',
            'pad': {'r': 10, 't': 87},
            'x': 0.1,
            'xanchor': 'right',
            'y': 0,
            'yanchor': 'top'
        }]
    )
    
    # 添加滑块
    fig.update_layout(
        sliders=[{
            'steps': [
                {
                    'args': [[f'frame_{i}'], {
                        'frame': {'duration': 0, 'redraw': True},
                        'mode': 'immediate',
                        'transition': {'duration': 0}
                    }],
                    'label': df.iloc[i]['date'].strftime('%m-%d'),
                    'method': 'animate'
                }
                for i in range(0, len(df), step)
            ],
            'active': 0,
            'currentvalue': {
                'font': {'size': 20},
                'prefix': '日期: ',
                'visible': True,
                'xanchor': 'right'
            },
            'len': 0.9,
            'x': 0.1,
            'xanchor': 'left',
            'y': 0,
            'yanchor': 'top'
        }]
    )
    
    fig.write_html('advanced_temperature_animation.html')
    print("高级气温动态图已保存为 advanced_temperature_animation.html")
    return fig

def create_weather_dashboard():
    """创建综合气象仪表板"""
    print("正在生成综合气象仪表板...")
    
    # 创建子图
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=('气温变化', '降水量', '太阳辐射', '气温vs太阳辐射', '月度统计', '极端天气'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]],
        vertical_spacing=0.08,
        horizontal_spacing=0.1
    )
    
    # 1. 气温变化 (左上)
    fig.add_trace(go.Scatter(x=df['date'], y=df['tmax_clean'], 
                            name='最高气温', line=dict(color='red')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['date'], y=df['tmin_clean'], 
                            name='最低气温', line=dict(color='blue')), row=1, col=1)
    
    # 2. 降水量 (右上)
    fig.add_trace(go.Bar(x=df['date'], y=df['rainfall'], 
                        name='降水量', marker_color='lightblue'), row=1, col=2)
    
    # 3. 太阳辐射 (中左)
    fig.add_trace(go.Scatter(x=df['date'], y=df['solar_radiation'], 
                            name='太阳辐射', line=dict(color='orange')), row=2, col=1)
    
    # 4. 气温vs太阳辐射散点图 (中右)
    fig.add_trace(go.Scatter(x=df['tmax_clean'], y=df['solar_radiation'], 
                            mode='markers', name='气温vs辐射',
                            marker=dict(size=5, color=df['rainfall'], 
                                      colorscale='Blues', showscale=True,
                                      colorbar=dict(title="降水量")),
                            hovertemplate='<b>最高气温</b>: %{x:.1f}°C<br>' +
                                        '<b>太阳辐射</b>: %{y:.1f}<br>' +
                                        '<b>降水量</b>: %{marker.color:.1f}mm<extra></extra>'), 
                   row=2, col=2)
    
    # 5. 月度统计 (左下)
    monthly_stats = df.groupby(df['date'].dt.month).agg({
        'tmax_clean': 'mean',
        'tmin_clean': 'mean',
        'rainfall': 'sum',
        'solar_radiation': 'mean'
    }).reset_index()
    
    fig.add_trace(go.Bar(x=monthly_stats['date'], y=monthly_stats['tmax_clean'], 
                        name='月均最高气温', marker_color='red'), row=3, col=1)
    fig.add_trace(go.Bar(x=monthly_stats['date'], y=monthly_stats['tmin_clean'], 
                        name='月均最低气温', marker_color='blue'), row=3, col=1)
    
    # 6. 极端天气 (右下) - 显示最高和最低温度
    extreme_high = df.nlargest(10, 'tmax_clean')
    extreme_low = df.nsmallest(10, 'tmin_clean')
    
    fig.add_trace(go.Scatter(x=extreme_high['date'], y=extreme_high['tmax_clean'], 
                            mode='markers', name='极端高温',
                            marker=dict(size=8, color='red', symbol='diamond')), row=3, col=2)
    fig.add_trace(go.Scatter(x=extreme_low['date'], y=extreme_low['tmin_clean'], 
                            mode='markers', name='极端低温',
                            marker=dict(size=8, color='blue', symbol='diamond')), row=3, col=2)
    
    # 更新布局
    fig.update_layout(
        title='2092年综合气象仪表板',
        title_x=0.5,
        height=1000,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # 更新坐标轴标签
    fig.update_xaxes(title_text="日期", row=1, col=1)
    fig.update_yaxes(title_text="温度 (°C)", row=1, col=1)
    fig.update_xaxes(title_text="日期", row=1, col=2)
    fig.update_yaxes(title_text="降水量 (mm)", row=1, col=2)
    fig.update_xaxes(title_text="日期", row=2, col=1)
    fig.update_yaxes(title_text="太阳辐射", row=2, col=1)
    fig.update_xaxes(title_text="最高气温 (°C)", row=2, col=2)
    fig.update_yaxes(title_text="太阳辐射", row=2, col=2)
    fig.update_xaxes(title_text="月份", row=3, col=1)
    fig.update_yaxes(title_text="温度 (°C)", row=3, col=1)
    fig.update_xaxes(title_text="日期", row=3, col=2)
    fig.update_yaxes(title_text="温度 (°C)", row=3, col=2)
    
    fig.write_html('weather_dashboard.html')
    print("综合气象仪表板已保存为 weather_dashboard.html")
    return fig

def create_seasonal_analysis():
    """创建季节性分析图"""
    print("正在生成季节性分析图...")
    
    # 添加季节信息
    df['season'] = df['date'].dt.month.map({
        12: '冬季', 1: '冬季', 2: '冬季',
        3: '春季', 4: '春季', 5: '春季',
        6: '夏季', 7: '夏季', 8: '夏季',
        9: '秋季', 10: '秋季', 11: '秋季'
    })
    
    # 季节性统计
    seasonal_stats = df.groupby('season').agg({
        'tmax_clean': ['mean', 'std'],
        'tmin_clean': ['mean', 'std'],
        'rainfall': ['sum', 'mean'],
        'solar_radiation': ['mean', 'std']
    }).round(2)
    
    # 创建季节性箱线图
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('各季节最高气温分布', '各季节最低气温分布', 
                       '各季节降水量分布', '各季节太阳辐射分布'),
        specs=[[{"type": "box"}, {"type": "box"}],
               [{"type": "box"}, {"type": "box"}]]
    )
    
    seasons = ['春季', '夏季', '秋季', '冬季']
    colors = ['green', 'red', 'orange', 'blue']
    
    for i, season in enumerate(seasons):
        season_data = df[df['season'] == season]
        
        # 最高气温箱线图
        fig.add_trace(go.Box(
            y=season_data['tmax_clean'],
            name=season,
            marker_color=colors[i],
            boxpoints='outliers'
        ), row=1, col=1)
        
        # 最低气温箱线图
        fig.add_trace(go.Box(
            y=season_data['tmin_clean'],
            name=season,
            marker_color=colors[i],
            boxpoints='outliers',
            showlegend=False
        ), row=1, col=2)
        
        # 降水量箱线图
        fig.add_trace(go.Box(
            y=season_data['rainfall'],
            name=season,
            marker_color=colors[i],
            boxpoints='outliers',
            showlegend=False
        ), row=2, col=1)
        
        # 太阳辐射箱线图
        fig.add_trace(go.Box(
            y=season_data['solar_radiation'],
            name=season,
            marker_color=colors[i],
            boxpoints='outliers',
            showlegend=False
        ), row=2, col=2)
    
    fig.update_layout(
        title='2092年季节性气象分析',
        title_x=0.5,
        height=800,
        showlegend=True
    )
    
    # 更新坐标轴标签
    fig.update_yaxes(title_text="最高气温 (°C)", row=1, col=1)
    fig.update_yaxes(title_text="最低气温 (°C)", row=1, col=2)
    fig.update_yaxes(title_text="降水量 (mm)", row=2, col=1)
    fig.update_yaxes(title_text="太阳辐射", row=2, col=2)
    
    fig.write_html('seasonal_analysis.html')
    print("季节性分析图已保存为 seasonal_analysis.html")
    
    # 打印季节性统计信息
    print("\n=== 季节性统计信息 ===")
    print(seasonal_stats)
    
    return fig

def main():
    """主函数"""
    print("开始生成高级气象动态图表...")
    
    try:
        # 生成各种高级图表
        create_advanced_temperature_animation()
        create_weather_dashboard()
        create_seasonal_analysis()
        
        print("\n所有高级图表生成完成！")
        print("生成的文件包括：")
        print("- advanced_temperature_animation.html (高级气温动态图)")
        print("- weather_dashboard.html (综合气象仪表板)")
        print("- seasonal_analysis.html (季节性分析图)")
        
    except Exception as e:
        print(f"生成图表时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 