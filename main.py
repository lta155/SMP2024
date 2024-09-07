import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor, as_completed

import dotenv
from autogen import Cache
from langchain_community.cache import SQLiteCache
from langchain_core.globals import set_llm_cache
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from tqdm import tqdm

from gpt4o import *
from tool.model import translate_prompt

dotenv.load_dotenv()


def run(item: dict):
    try:
        content = item["content"]

        # Use DiskCache as cache
        with Cache.disk(cache_path_root="./autogen_cache", cache_seed=1) as cache:
            chat_result = code_executor_agent.initiate_chat(
                code_writer_agent,
                message=content,
                summary_method='reflection_with_llm',
                summary_args=dict(summary_prompt='only return the code output'),
                cache=cache,
                silent=True,
            )
        # code = extract_python_code(chat_result.chat_history[-3]['content'])[-1]
        code = ""
        for i in range(len(chat_result.chat_history) - 1, 0, -1):
            l = extract_python_code(chat_result.chat_history[i]['content'])
            if len(l) > 0:
                code = l[-1]
                break

        answer = chat_result.summary
        if isinstance(answer, dict):
            answer = answer['content']
        item["code"] = code
        item["answer"] = answer
        item['chat_history'] = chat_result.chat_history
        return item
    except Exception as e:
        print(e)
        return f"Error processing item {item['ID']}: {str(e)}"

def run_concurrent(items):
    results = []
    try:
        with multiprocessing.Pool(processes=5) as pool:
            # 使用 `tqdm` 显示进度条
            for result in tqdm(pool.imap_unordered(run, items), total=len(items)):
                if result is not None:
                    results.append(result)  # 仅记录成功的任务结果
                else:
                    print(f"Task failed.")
    except Exception as e:
        print(f"An error occurred during the concurrent execution: {e}")

    return results


if __name__ == "__main__":
    with open('data/Final_TestSet/Final_TestSet.json', 'r', encoding='utf-8') as f:
        dataset_init = json.load(f)
    with open('data/Final_Example.json', 'r', encoding='utf-8') as f:
        preliminary_example = json.load(f)

    for i in range(0, len(dataset_init)):
        # 检查数据集文件是否一致
        assert dataset_init[i]["ID"] == preliminary_example[i]["ID"]
        assert dataset_init[i]["question"] == preliminary_example[i]["question"]

    print("样本数量：", len(dataset_init))
    print("问题类型：", ",".join(set([item["problem_type"] for item in dataset_init])))
    FROM = 0
    TO = FROM + 512
    dataset = dataset_init[FROM:TO]

    print("运行")
    ### 预处理
    for i in range(0, len(dataset)):
        content = d_template[dataset[i]["problem_type"]].format(dataset[i]["question"])
        filenames = extract_filenames(content)
        for filename in filenames:
            content = content.replace(filename, add_path(filename, data_path / 'Final_TestSet/data'))
        dataset[i]["content"] = content

    new_dataset=run_concurrent(dataset[:100])

    print("验证")
    new_dataset=sorted(new_dataset,key=lambda x: x['ID'])

    print("存储")
    with open('data/SMP_240905_check_2.json', 'w', encoding='utf-8') as f:
        s = json.dumps(new_dataset, indent=4, ensure_ascii=False)
        f.write(s)

