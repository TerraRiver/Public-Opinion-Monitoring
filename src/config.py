from pathlib import Path

# 获取项目根目录 (假设 config.py 位于 src/ 下，根目录就是它的上级再上级)
# 这里指向的是包含 src 文件夹的那个目录
PROJECT_DIR = Path(__file__).resolve().parents[1]

# 数据路径
DATA_DIR = PROJECT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
INTERIM_DATA_DIR = DATA_DIR / "interim"
EXTERNAL_DATA_DIR = DATA_DIR / "external"

# 结果路径
FIGURES_DIR = PROJECT_DIR / "results" / "figures"
TABLES_DIR = PROJECT_DIR / "results" / "tables"

# 确保核心目录存在 (防止手动删除后报错)
for path in [DATA_DIR, FIGURES_DIR, TABLES_DIR]:
    path.mkdir(parents=True, exist_ok=True)