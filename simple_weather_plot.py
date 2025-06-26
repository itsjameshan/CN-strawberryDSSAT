import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 读取数据
print("正在读取数据...")
df = pd.read_csv('weather_data.csv')
df['date'] = pd.to_datetime(df['date'])
print(f"数据加载完成，共 {len(df)} 条记录")

# 简单的气温动态图
def simple_temperature_plot():
    """创建简单的气温动态图"""
    print("正在生成气温动态图...")
    
    fig = px.line(df, x='date', y=['tmax', 'tmin'], 
                  title='2092年气温变化图',
                  labels={'value': '温度 (°C)', 'date': '日期', 'variable': '温度类型'},
                  color_discrete_map={'tmax': 'red', 'tmin': 'blue'})
    
    fig.update_layout(
        title_x=0.5,
        xaxis_title="日期",
        yaxis_title="温度 (°C)",
        hovermode='x unified'
    )
    
    # 保存为HTML文件
    fig.write_html('simple_temperature.html')
    print("气温图已保存为 simple_temperature.html")
    
    # 显示图表（可选）
    # fig.show()

# 简单的降水量柱状图
def simple_rainfall_plot():
    """创建简单的降水量柱状图"""
    print("正在生成降水量图...")
    
    fig = px.bar(df, x='date', y='rainfall', 
                 title='2092年降水量变化图',
                 labels={'rainfall': '降水量 (mm)', 'date': '日期'},
                 color='rainfall',
                 color_continuous_scale='Blues')
    
    fig.update_layout(
        title_x=0.5,
        xaxis_title="日期",
        yaxis_title="降水量 (mm)"
    )
    
    fig.write_html('simple_rainfall.html')
    print("降水量图已保存为 simple_rainfall.html")

# 简单的太阳辐射图
def simple_solar_plot():
    """创建简单的太阳辐射图"""
    print("正在生成太阳辐射图...")
    
    fig = px.line(df, x='date', y='solar_radiation',
                  title='2092年太阳辐射变化图',
                  labels={'solar_radiation': '太阳辐射', 'date': '日期'})
    
    fig.update_layout(
        title_x=0.5,
        xaxis_title="日期",
        yaxis_title="太阳辐射"
    )
    
    fig.write_html('simple_solar.html')
    print("太阳辐射图已保存为 simple_solar.html")

# 数据统计信息
def show_data_info():
    """显示数据基本信息"""
    print("\n=== 数据基本信息 ===")
    print(f"数据时间范围: {df['date'].min()} 到 {df['date'].max()}")
    print(f"最高气温范围: {df['tmax'].min():.1f}°C 到 {df['tmax'].max():.1f}°C")
    print(f"最低气温范围: {df['tmin'].min():.1f}°C 到 {df['tmin'].max():.1f}°C")
    print(f"降水量范围: {df['rainfall'].min():.1f}mm 到 {df['rainfall'].max():.1f}mm")
    print(f"太阳辐射范围: {df['solar_radiation'].min():.1f} 到 {df['solar_radiation'].max():.1f}")
    
    # 计算一些统计信息
    print(f"\n=== 统计信息 ===")
    print(f"平均最高气温: {df['tmax'].mean():.1f}°C")
    print(f"平均最低气温: {df['tmin'].mean():.1f}°C")
    print(f"总降水量: {df['rainfall'].sum():.1f}mm")
    print(f"平均太阳辐射: {df['solar_radiation'].mean():.1f}")

# 主函数
def main():
    """主函数"""
    print("开始生成气象图表...")
    
    try:
        # 显示数据信息
        show_data_info()
        
        # 生成简单图表
        simple_temperature_plot()
        simple_rainfall_plot()
        simple_solar_plot()
        
        print("\n所有图表生成完成！")
        print("生成的文件：")
        print("- simple_temperature.html")
        print("- simple_rainfall.html") 
        print("- simple_solar.html")
        
    except Exception as e:
        print(f"生成图表时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 