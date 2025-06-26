"""Helper script to execute the original DSSAT strawberry model."""

from cropgro_strawberry_implementation import run_example_simulation

if __name__ == "__main__":
    # 运行模型，获取结果
    model, results, fig = run_example_simulation()
    # 保存为指定csv文件
    results.to_csv('run_original_dssat.csv', index=False)
    print("模拟结果已保存为 run_original_dssat.csv")
