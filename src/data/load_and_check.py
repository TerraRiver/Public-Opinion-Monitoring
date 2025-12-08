import pandas as pd
def load_raw_data():
    """
    加载指定目录下所有的 JSON 数据并合并
    """
    # 获取原始数据地址
    from src import config
    raw_data_path = config.RAW_DATA_DIR

    # 获取所有 JSON 文件列表
    # json_files列表存储所有 JSON 文件
    json_files = sorted(list(raw_data_path.glob('*.json')))
    print(f"共发现 {len(json_files)} 个 JSON 文件，准备开始加载...")

    # 用于临时存储每个文件的 DataFrame
    dfs = [] 

    # 循环读取每个文件
    for i, file_path in enumerate(json_files, 1):
        try:
            print(f"[{i}/{len(json_files)}] 正在读取: {file_path.name}")
            # 读取单个 JSON
            temp_df = pd.read_json(file_path)
            
            # 保留你原有的逻辑：展开 articles 字段
            # 注意：如果某个文件是空的或结构不对，这里可能会报错，建议加上 try-except
            if 'articles' in temp_df.columns:
                temp_df = temp_df['articles'].apply(pd.Series)
                dfs.append(temp_df)
            else:
                print(f"警告: 文件 {file_path.name} 中不包含 'articles' 字段，已跳过。")
                
        except Exception as e:
            print(f"错误: 读取文件 {file_path.name} 失败. 原因: {e}")

    # 合并所有数据
    final_df = pd.concat(dfs, ignore_index=True)
    print(f"合并完成，共 {len(final_df)} 条新闻。")

    return final_df

def check_data(df):
    """
    详细检查 DataFrame 的缺失值情况，返回统计表
    """
    # 1. 计算缺失值数量
    total = df.isnull().sum()
    # 2. 计算缺失值百分比
    percent = (df.isnull().sum() / len(df)) * 100
    # 3. 获取各列数据类型 (有助于判断是数值缺失还是字符缺失)
    dtypes = df.dtypes
    # 4. 合并成一个新的 DataFrame
    missing_data = pd.concat([total, percent, dtypes], axis=1, keys=['Total', 'Percent (%)', 'Type'])
    # 5. 按缺失值数量降序排列
    missing_data = missing_data.sort_values('Total', ascending=False)
    # 6. 只保留有缺失值的列（让输出更干净）
    missing_data = missing_data[missing_data['Total'] > 0]
    print(f"数据总行数: {len(df)}")
    if missing_data.empty:
        print("完美！没有发现缺失值。")
    else:
        print(f"发现 {len(missing_data)} 个列包含缺失值：")
        # 打印结果（如果是在 Jupyter 中，直接返回 missing_data 会显示漂亮的表格）
        display(missing_data) if 'display' in locals() else print(missing_data)
    return missing_data

def load_clean_data():
    """
    加载清理后的数据
    """
    # 获取原始数据地址
    from src import config
    clean_data_path = config.PROCESSED_DATA_DIR / 'cleaned_data.csv'
    classify_data_path = config.PROCESSED_DATA_DIR / 'classify_data.csv'

    # 加载数据
    df = pd.read_csv(clean_data_path)
    df.to_csv(classify_data_path, index=False)

    df = pd.read_csv(classify_data_path)
    return df

def load_classify_data():
    """
    加载分类后的数据，并自动剔除不在合法分类列表中的行（如 Error 或 None）
    """
    import pandas as pd
    from src import config
    
    # 1. 定义合法分类标准
    VALID_CATEGORIES = [
        "中印边界/边境问题",
        "西藏/达赖喇嘛问题",
        "台湾问题",
        "一带一路与周边地缘",
        "中印经贸与科技",
        "中国经济现状",
        "中印军力与国防",
        "中国国内政治",
        "中印双边关系",
        "中国外交",
        "中印签证与人文"
    ]

    classify_data_path = config.PROCESSED_DATA_DIR / 'classify_data.csv'
    result_data_path = config.PROCESSED_DATA_DIR / 'result_data.csv'

    # 2. 加载数据
    df = pd.read_csv(classify_data_path)
    
    # 3. 【新增功能】执行过滤
    original_count = len(df)
    # 只保留 category 列的值在 VALID_CATEGORIES 列表中的行
    df = df[df['category'].isin(VALID_CATEGORIES)]
    
    # (可选) 打印清洗日志
    dropped_count = original_count - len(df)
    if dropped_count > 0:
        print(f"🧹 已自动剔除 {dropped_count} 条无效/错误分类数据 (剩余 {len(df)} 条)")

    # 4. 保存清洗后的结果
    df.to_csv(result_data_path, index=False, encoding='utf-8-sig')

    # 5. 返回结果
    # (通常不需要重新 read_csv，直接返回 df 即可，但为了保持你原有逻辑不做改动)
    df = pd.read_csv(result_data_path)
    return df