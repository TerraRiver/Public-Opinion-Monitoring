import pandas as pd
from src import config
def basic_clean(df):
    """基础清理函数"""
    print("-" * 50) # 打印分隔线
    # 规范化日期结构
    print("正在规范化时间格式")
    print(f"转换前的pub_time示例: {df.iloc[5]['pub_date']}")
    df['publish_date'] = pd.to_datetime(df['pub_date'])
    print(f"转换后的publish_date示例: {df.iloc[5]['publish_date']}")
    # 删除不需要的列
    print("正在删除不需要数据列")
    df = df.drop(columns=['pub_time','pub_date','author','words', 'language', 'company', 'industry', 'subject', 'region', 'layout', 'abstracts'])
    print(f"剩余列名如下: {df.columns.tolist()}")
    # 重命名列
    print("正在重命名列")
    df.rename(columns={
    'headline': 'title',
    'source': 'source_media'
    }, inplace=True)
    print(f"重命名后列名如下: {df.columns.tolist()}")
    # 去除重复数据（重复判定规则为标题+内容）
    num_1 = len(df)
    print("正在去除重复数据，去除前数据量为:", num_1)
    df.drop_duplicates(subset=['title', 'content'], inplace=True)
    num_2 = len(df)
    print("共去除重复数据:", num_1 - num_2, "去除后数据量为:", num_2)
    print("-" * 50) # 打印分隔线
    return df

def meida_clean(df, blacklist_keywords=config.BLACK_MEDIAS):
    """
    清洗媒体来源函数
    :param df: 输入的 DataFrame
    :param blacklist_keywords: (可选) 包含要剔除的媒体关键词列表，例如 ['Agency', 'Unknown']
    """
    print("-" * 50) 
    print("【开始媒体清洗流程】")
    # --- 1. 保存原始分布 ---
    source_counts = df['source_media'].value_counts()
    source_counts.to_csv(
        config.TABLES_DIR / '源数据媒体来源分布.csv', 
        sep='\t', 
        header=['文章数量'], 
        index_label='媒体来源',
        encoding='utf-8-sig'
    )
    print(f"原始数据总量: {len(df)} 条")
    print("原始媒体分布已保存至: tables/源数据媒体来源分布.csv")
    # --- 2. 黑名单剔除 (新增功能) ---
    if blacklist_keywords:
        print(f"\n--- 正在执行黑名单过滤 ---")
        print(f"黑名单关键词: {blacklist_keywords}")
        original_count = len(df)
        # 构建正则模式，一次性匹配所有关键词 (使用 | 连接)
        # regex=False 关闭正则模式，纯字符串匹配，防止括号等符号报错；
        # 但如果要匹配多个词，建议用循环或构建 pattern。
        # 这里使用最稳妥的循环方式，逐个剔除：
        for keyword in blacklist_keywords:
            # case=False 忽略大小写
            mask = df['source_media'].str.contains(keyword, case=False, na=False)
            deleted_count = mask.sum()
            if deleted_count > 0:
                print(f" -> 剔除包含 '{keyword}' 的数据: {deleted_count} 条")
                df = df[~mask] # ~ 表示取反，保留不包含的数据
        print(f"黑名单清洗后剩余: {len(df)} 条 (共移除 {original_count - len(df)} 条)")
    # --- 3. 媒体来源合并与标准化 ---
    print("\n--- 正在进行媒体来源合并与标准化 ---")
    # 建立映射字典 (比多行 loc 更易维护)
    replacements = {
        'Times of India': 'The Times of India',
        'Economic Times': 'The Economic Times',
        'India Today': 'India Today',
        'Indian Express': 'Indian Express',
        'Financial Express': 'Financial Express',
        'BusinessLine': 'BusinessLine', # 这里把 BusinessLine Online 统一为 BusinessLine
        'The Hindu': 'The Hindu'
    }
    for key, target in replacements.items():
        # 将包含 key 的都改为 target
        df.loc[df['source_media'].str.contains(key, case=False, na=False), 'source_media'] = target
    # --- 4. 保存清洗后分布 ---
    source_counts_final = df['source_media'].value_counts()
    source_counts_final.to_csv(
        config.TABLES_DIR / '清洗后媒体来源分布.csv', 
        sep='\t', 
        header=['文章数量'], 
        index_label='媒体来源',
        encoding='utf-8-sig'
    )
    print("合并后媒体分布已保存至: tables/清洗后媒体来源分布.csv")
    print("-" * 50)
    return df

def data_save(df):
    print(f"清洗完成后数据总条数为{len(df)}")
    print(f"正在保存最终清洗数据到: {config.PROCESSED_DATA_DIR}")
    df.to_csv(
        config.PROCESSED_DATA_DIR / 'cleaned_data.csv', 
        index=False,          # 通常不保存pandas自动生成的数字索引
        encoding='utf-8-sig'  # 使用 utf-8-sig 确保 Excel 打开中文不乱码
    )
    print("数据保存完成。")
    return None