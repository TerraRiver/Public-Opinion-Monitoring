import matplotlib.pyplot as plt
import seaborn as sns
import platform

def Matplotlib_Seaborn_style():
    # 设置 Matplotlib 和 Seaborn 样式
    # 重置默认配置
    plt.rcdefaults()
    # 设置 Seaborn 主题为 "ticks" (白色背景，有刻度)，上下文为 "paper" (适合论文的大小)
    sns.set_theme(style="ticks", context="paper", font_scale=1.2)
    # 判断操作系统以选择合适的衬线中文字体
    system_name = platform.system()
    if system_name == "Windows":
        font_list = ['Times New Roman', 'SimSun', 'STSong'] # Windows: Times + 宋体
    elif system_name == "Darwin":
        font_list = ['Times New Roman', 'Songti SC', 'STSong'] # Mac: Times + 宋体
    else:
        font_list = ['Times New Roman', 'Noto Serif CJK SC', 'WenQuanYi Zen Hei'] # Linux
    # Matplotlib 深度定制
    plt.rcParams.update({
        'font.family': 'serif',          # 强制使用衬线体
        'font.serif': font_list,         # 设定衬线字体优先列表
        'axes.unicode_minus': False,     # 解决负号显示问题
        'mathtext.fontset': 'stix',      # 数学公式使用类 LaTeX 字体
        'figure.figsize': (10, 6),       # 默认图表大小
        'axes.labelsize': 12,            # 轴标签字号
        'xtick.labelsize': 10,           # X轴刻度字号
        'ytick.labelsize': 10,           # Y轴刻度字号
        'axes.linewidth': 1.0,           # 坐标轴线宽
        'grid.linestyle': '--',          # 网格线样式（如果开启）
        'grid.alpha': 0.3,               # 网格线透明度
        'savefig.dpi': 300,              # 保存分辨率
        'savefig.bbox': 'tight'          # 保存时自动裁剪空白
    })
    print(f"完成可视化设置，当前系统: {system_name}，字体配置优先顺序: {font_list[1]}")

    return None