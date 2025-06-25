import pandas as pd
import matplotlib.pyplot as plt

# 读取数据
df = pd.read_csv('草莓.csv')

# 1. 生物量随天数变化
plt.figure(figsize=(8,5))
plt.plot(df['dap'], df['biomass'], marker='o', label='生物量 (biomass)')
plt.xlabel('天数 (dap)')
plt.ylabel('生物量 (biomass)')
plt.title('生物量随天数变化')
plt.legend()
plt.grid(True)
plt.show()

# 2. 叶面积指数随天数变化
plt.figure(figsize=(8,5))
plt.plot(df['dap'], df['leaf_area_index'], marker='o', color='g', label='叶面积指数 (LAI)')
plt.xlabel('天数 (dap)')
plt.ylabel('叶面积指数 (leaf_area_index)')
plt.title('叶面积指数随天数变化')
plt.legend()
plt.grid(True)
plt.show()

# 3. 根系深度随天数变化
plt.figure(figsize=(8,5))
plt.plot(df['dap'], df['root_depth'], marker='o', color='orange', label='根系深度 (root_depth)')
plt.xlabel('天数 (dap)')
plt.ylabel('根系深度 (root_depth)')
plt.title('根系深度随天数变化')
plt.legend()
plt.grid(True)
plt.show()

# 4. 光合速率随天数变化
plt.figure(figsize=(8,5))
plt.plot(df['dap'], df['photosynthesis'], marker='o', color='purple', label='光合速率 (photosynthesis)')
plt.xlabel('天数 (dap)')
plt.ylabel('光合速率 (photosynthesis)')
plt.title('光合速率随天数变化')
plt.legend()
plt.grid(True)
plt.show()