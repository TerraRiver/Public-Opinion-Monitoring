from src import config
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time
import pandas as pd
from tqdm import tqdm
from threading import Lock
from openai import OpenAI, BadRequestError, RateLimitError, APITimeoutError, APIConnectionError

def clean_json_string(text):
    """清洗 JSON 字符串"""
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return text

def call_llm_classify(title, content, retries=5):
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
                    {"role": "system", "content": config.SYSTEM_PROMPT_01},
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

def llm_classify_concurrently(
    df, 
    output_csv_path=config.PROCESSED_DATA_DIR / 'classify_data.csv', 
    max_workers=None,  # 默认 None,让系统自动决定
    save_interval=15   # 每处理 15 条保存一次
):
    """
    并发处理 DataFrame,带性能监控和进度保存
    """
    
    # 定义标准的 12 个合法分类列表
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
        "中印签证与人文",
        "其他"
    ]

    # 1. 初始化列
    if 'category' not in df.columns:
        df['category'] = None
    if 'reason' not in df.columns:
        df['reason'] = None
        
    # 2. 筛选需要处理的行
    mask_to_process = ~df['category'].isin(VALID_CATEGORIES)
    indices_to_process = df[mask_to_process].index.tolist()
    
    print(f"📊 总行数: {len(df)}")
    print(f"🔄 本次需处理: {len(indices_to_process)} 行")
    print(f"✅ 已完成: {len(df) - len(indices_to_process)} 行")
    
    if not indices_to_process:
        print("🎉 所有数据已完美处理完毕!")
        return df

    # 3. 自动设置线程数
    if max_workers is None:
        max_workers = min(10, len(indices_to_process))  # 最多 32 线程
    
    print(f"\n⚙️ 并发配置:")
    print(f"  - 线程数: {max_workers}")
    print(f"  - 每条重试: 5 次")
    print(f"  - 自动保存间隔: 每 {save_interval} 条")
    
    # 4. 性能监控
    start_time = time.time()
    completed_count = 0
    lock = Lock()  # 用于线程安全地更新计数器
    
    def update_and_save(idx, result):
        """线程安全的更新和保存函数"""
        nonlocal completed_count
        
        # 【修改点 1】扩大 Lock 范围，包含写入操作，防止读写冲突
        with lock:
            if result: 
                df.at[idx, 'category'] = result.get('category')
                df.at[idx, 'reason'] = result.get('reason')
            else:
                df.at[idx, 'category'] = "Error"
                df.at[idx, 'reason'] = "Failed after 5 retries"
        
            completed_count += 1
            
            # 定期保存
            if completed_count % save_interval == 0:
                # 【修改点 2】增加 try-except，防止文件占用导致程序崩溃
                try:
                    df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
                    elapsed = time.time() - start_time
                    rate = completed_count / elapsed
                    print(f"\n💾 已保存进度: {completed_count}/{len(indices_to_process)} ({rate:.2f} 条/秒)")
                except Exception as e:
                    print(f"\n⚠️ 自动保存失败 (不影响运行，请检查文件是否被占用): {e}")
    
    # 5. 并发执行
    print(f"\n🚀 开始并发处理...\n")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(
                call_llm_classify,           
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
                print(f"\n❌ Row {idx} 异常: {e}")
                # 【修改点 3】确保异常处理时也安全写入并尝试保存
                with lock:
                    df.at[idx, 'category'] = "Error"
                    df.at[idx, 'reason'] = str(e)
                    completed_count += 1
                    # 也可以在这里加上保存逻辑，或者依赖下一次成功时的保存

    # 6. 最终保存
    try:
        df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
        print(f"\n✅ 最终保存成功!")
    except Exception as e:
        print(f"\n❌ 最终保存失败: {e}")
    
    # 7. 性能报告
    total_time = time.time() - start_time
    avg_rate = len(indices_to_process) / total_time
    
    print(f"\n{'='*60}")
    print(f"✅ 处理完成!")
    print(f"📈 性能统计:")
    print(f"  - 总耗时: {total_time:.2f} 秒")
    print(f"  - 平均速度: {avg_rate:.2f} 条/秒")
    print(f"  - 处理总数: {len(indices_to_process)} 条")
    
    # 8. 最终统计
    remaining_invalid = df[~df['category'].isin(VALID_CATEGORIES)]
    if len(remaining_invalid) > 0:
        print(f"\n⚠️ 仍有 {len(remaining_invalid)} 条未归入合法分类")
        print(f"   建议: 重新运行此函数")
    else:
        print(f"\n🎊 完美! 所有数据均已归入标准分类")
    print(f"{'='*60}\n")
    
    return df


# ============ 测试并发是否生效的诊断函数 ============

def test_concurrency(num_requests=20, max_workers=10):
    """
    快速测试并发是否真正生效
    返回: (总耗时, 理论单线程耗时, 加速比)
    """
    print(f"🧪 并发测试: {num_requests} 个请求, {max_workers} 个线程\n")
    
    # 模拟 API 调用(每次耗时 2 秒)
    def mock_api_call(idx):
        time.sleep(2)  # 模拟 API 延迟
        return f"Result {idx}"
    
    # 单线程测试
    print("1️⃣ 单线程测试...")
    start = time.time()
    for i in range(num_requests):
        mock_api_call(i)
    single_thread_time = time.time() - start
    print(f"   耗时: {single_thread_time:.2f} 秒\n")
    
    # 多线程测试
    print(f"2️⃣ {max_workers} 线程测试...")
    start = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(mock_api_call, range(num_requests)))
    multi_thread_time = time.time() - start
    print(f"   耗时: {multi_thread_time:.2f} 秒\n")
    
    # 结果
    speedup = single_thread_time / multi_thread_time
    print(f"{'='*50}")
    print(f"📊 测试结果:")
    print(f"  单线程耗时: {single_thread_time:.2f} 秒")
    print(f"  多线程耗时: {multi_thread_time:.2f} 秒")
    print(f"  加速比: {speedup:.2f}x")
    
    if speedup > 2:
        print(f"  ✅ 并发工作正常!")
    else:
        print(f"  ⚠️ 并发效果不明显,可能受到 API 限流影响")
    print(f"{'='*50}")
    
    return multi_thread_time, single_thread_time, speedup