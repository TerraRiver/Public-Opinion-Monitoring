from src import config
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from src.utils import Matplotlib_Seaborn_style

def media_visualization(df):
    # 设置可视化样式
    Matplotlib_Seaborn_style()
    print("正在生成合并筛选后媒体来源分布图")
    media_counts= df['source_media'].value_counts()

    # 创建画布
    fig, ax = plt.subplots(figsize=(10, 6)) # 显式创建对象以便更好地控制
    # 绘制条形图
    # palette 使用 "mako" (深蓝绿色系) 或 "gray" (灰度) 更符合黑白印刷或学术风格
    # zorder=3 让柱状图浮在网格线之上
    sns.barplot(
        x=media_counts.values, 
        y=media_counts.index, 
        palette="mako", 
        ax=ax,
        edgecolor="black", # 给柱子加黑边，增强对比度
        linewidth=0.8,
        zorder=3
    )
    # 标题和标签 (使用 Times New Roman 风格的字体)
    ax.set_title('媒体来源分布图', fontweight='bold', pad=20)
    ax.set_xlabel('文章数量')
    ax.set_ylabel('媒体来源')
    # 学术图表关键调整：去边框 (Despine)
    sns.despine(trim=True) # 去掉上方和右侧边框，trim=True 让坐标轴线只延伸到数据范围内
    # 仅在 X 轴添加轻微的网格线辅助读数
    ax.grid(axis='x', linestyle='--', alpha=0.4, zorder=0)
    # 保存图片
    save_path = config.FIGURES_DIR / '媒体来源分布图.png'
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print("媒体来源分布图已保存至:", config.FIGURES_DIR / '媒体来源分布图.png')
    print("-" * 50) # 打印分隔线