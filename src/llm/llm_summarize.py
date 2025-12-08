from src import config
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time
import threading  # 1. 必须导入 threading
import pandas as pd
from tqdm import tqdm
# 2. 引入 BadRequestError 以捕获 400 错误
from openai import OpenAI, BadRequestError, RateLimitError, APITimeoutError, APIConnectionError

def clean_json_string(text):
    """清洗 JSON 字符串"""
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return text

def call_llm_summarize(title, content, retries=5):
    """
    使用 OpenAI SDK 兼容模式调用 Zenmux/Gemini 进行总结
    """
    client = OpenAI(
        api_key=config.API_KEY,
        base_url=config.API_URL  # 直接使用完整 URL，无需手动 strip "/v1"
    )
    
    user_content = f"Headline: {title}\n\nArticle Content: {content}"
    
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=config.MODEL_NAME, # 确保 config 中已更新为 "google/gemini-3-pro-preview"
                messages=[
                    {"role": "system", "content": config.SYSTEM_PROMPT_02},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}, # Gemini 支持 JSON 模式
                timeout=120,
                stream=False
            )
            
            # 2. 增加对 finish_reason 的检查 (Gemini 敏感内容过滤机制)
            finish_reason = response.choices[0].finish_reason
            if finish_reason == "content_filter":
                print(f"⚠️ 内容安全拦截 (Gemini): {title[:15]}...")
                return None
            
            result_text = response.choices[0].message.content
            
            # 确保 helper 函数存在，如果不存在需补充定义
            return json.loads(clean_json_string(result_text))

        # 3. 错误处理 (适配通用 OpenAI 协议)
        except BadRequestError as e:
            err_msg = str(e)
            # DeepSeek 的 "Content Exists Risk" 在这里可能表现为其他 400 错误
            # 如果是内容安全问题，通常不需要重试
            if 'safety' in err_msg.lower() or 'filter' in err_msg.lower() or 'content' in err_msg.lower():
                print(f"⚠️ 内容敏感/请求拒绝 (跳过): {title[:15]}... 错误信息: {e}")
                return None 
            else:
                print(f"❌ 参数错误 (BadRequest): {e}")
                return None
        
        except RateLimitError:
            sleep_time = 5 * (attempt + 1)
            print(f"⚠️ 429 限流, 等待 {sleep_time}s...")
            time.sleep(sleep_time)
            
        except (APITimeoutError, APIConnectionError) as e:
            print(f"⚠️ 网络/超时问题: {e}, 重试中...")
            time.sleep(2)
            
        except json.JSONDecodeError:
            print(f"❌ JSON 解析失败，可能是模型输出格式错误。重试中...")
            # 可以选择重试，或者直接 continue
            
        except Exception as e:
            print(f"❌ 未知异常: {e}")
            time.sleep(2)
            
    return None
def llm_summarize_concurrently(
    df, 
    output_csv_path=config.PROCESSED_DATA_DIR / 'result_data.csv', 
    max_workers=None, 
    save_interval=15 
):
    # 4. 初始化线程锁
    lock = threading.Lock()

    # 初始化列
    required_columns = {
        'Chinese_Entities': None,
        'Indian_Entities': None,
        'Sentiment_Score': None,
        'Summary_CN': None,
        'Summary_EN': None
    }
    
    for col, default_val in required_columns.items():
        if col not in df.columns:
            df[col] = default_val
        
    mask_to_process = (
        df['Summary_CN'].isna() | 
        (df['Summary_CN'] == "") | 
        (df['Summary_CN'] == "Error")
    )
    indices_to_process = df[mask_to_process].index.tolist()
    
    print(f"📊 总行数: {len(df)}")
    print(f"🔄 本次需处理: {len(indices_to_process)} 行")
    
    if not indices_to_process:
        return df

    if max_workers is None:
        max_workers = min(10, len(indices_to_process))
    
    # 性能监控变量
    start_time = time.time()
    completed_count = 0
    error_count = 0
    
    def update_and_save(idx, result):
        nonlocal completed_count, error_count
        
        # 5. 使用定义好的 lock
        with lock:
            if result:
                df.at[idx, 'Chinese_Entities'] = result.get('Chinese_Entities')
                df.at[idx, 'Indian_Entities'] = result.get('Indian_Entities')
                df.at[idx, 'Sentiment_Score'] = result.get('Sentiment_Score')
                df.at[idx, 'Summary_CN'] = result.get('Summary_CN')
                df.at[idx, 'Summary_EN'] = result.get('Summary_EN')
            else:
                # 结果为 None (包括敏感内容触发的情况)
                df.at[idx, 'Summary_CN'] = "Error"
                df.at[idx, 'Summary_EN'] = "Failed/Sensitive"
                df.at[idx, 'Sentiment_Score'] = -999
                error_count += 1
            
            completed_count += 1
            
            if completed_count % save_interval == 0:
                df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
                elapsed = time.time() - start_time
                rate = completed_count / elapsed
                print(f"\n💾 已保存: {completed_count}/{len(indices_to_process)} ({rate:.2f} it/s, Err: {error_count})")
    
    print(f"\n🚀 开始并发处理 (Workers: {max_workers})...\n")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(
                call_llm_summarize,           
                df.at[idx, 'title'],         
                df.at[idx, 'content'],
                5
            ): idx 
            for idx in indices_to_process
        }
        
        for future in tqdm(as_completed(future_to_index), total=len(indices_to_process), desc="🔥 LLM Processing"):
            idx = future_to_index[future]
            try:
                result = future.result()
                update_and_save(idx, result)     
            except Exception as e:
                print(f"\n❌ Row {idx} 线程异常: {e}")
                # 异常发生时的兜底保存
                with lock: 
                    df.at[idx, 'Summary_CN'] = "Error"
                    error_count += 1

    df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 处理完成! 错误数: {error_count}")
    return None