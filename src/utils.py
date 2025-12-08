import pandas as pd
from pathlib import Path

def get_project_root() -> Path:
    """返回项目根目录"""
    return Path(__file__).resolve().parents[1]

def load_data(filename: str, folder="raw"):
    """
    辅助函数：从 data 目录读取文件
    用法: df = load_data("my_data.csv", folder="processed")
    """
    # 避免循环导入，这里重新计算路径或导入 config
    from src import config
    
    base_path = config.DATA_DIR / folder
    file_path = base_path / filename
    
    if not file_path.exists():
        raise FileNotFoundError(f"文件未找到: {file_path}")
        
    if filename.endswith('.csv'):
        return pd.read_csv(file_path)
    elif filename.endswith('.xlsx'):
        return pd.read_excel(file_path)
    # 根据需要添加更多格式 (dta, sav 等)
    return None