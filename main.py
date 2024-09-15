import multiprocessing
import os

import agentops
import dotenv
from tqdm import tqdm

from gpt4o import *

dotenv.load_dotenv()

file_name="SMP_240915_answer_1"
def run(id_and_content: str):
    cache_seed = 1
    file_name = "SMP_240915_answer_1"
    ID, content = id_and_content.split("@####@")
    agentops.init(tags=["ID:" + ID,file_name])
    try:

        # Use DiskCache as cache
    # with Cache.disk(cache_path_root="./autogen_cache", cache_seed=cache_seed) as cache:
        chat_result = code_executor_agent.initiate_chat(
            code_writer_agent,
            message=content,
            summary_method='reflection_with_llm',
            summary_args=dict(summary_prompt='only return the code output'),
            # cache=cache,
            silent=True,
        )
        agentops.end_session('Success')
        code = ""
        for i in range(len(chat_result.chat_history) - 1, 0, -1):
            l = extract_python_code(chat_result.chat_history[i]['content'])
            if len(l) > 0:
                code = l[-1]
                break

        answer = chat_result.summary
        if isinstance(answer, dict):
            answer = answer['content']
        # item['chat_history']=chat_result.chat_history
        return ID+"@####@"+code+"@####@"+answer
    except Exception as e:
        agentops.end_session('Failure')
        print(f"Error processing item {ID}: {str(e)}")
        return f"Error processing item {ID}: {str(e)}"

def run_concurrent(items):
    results = []
    try:
        with multiprocessing.Pool(processes=10) as pool:
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
        dataset = json.load(f)
    with open('data/Final_TestSet/id_and_content.json', 'r', encoding='utf-8') as f:
        id_and_content = json.load(f)
    # 判断文件存在
    if os.path.exists(f'data/Final_TestSet/{file_name}.json'):
        with open(f'data/Final_TestSet/{file_name}.json', 'r', encoding='utf-8') as f:
            answers=json.load(f)
    else:
        answers=[]

    print("预处理")
    _id=[i["ID"] for i in answers if "answer" in i]
    id_and_content=[i for i in id_and_content if i.split("@####@")[0] not in _id]

    print(f"运行,共{len(id_and_content)}")
    id_and_code_and_answer=run_concurrent(id_and_content)
    id_and_code_and_answer = sorted([i.split("@####@") for i in id_and_code_and_answer], key=lambda x: x[0],
                                    reverse=False)
    print("验证")
    for i in range(len(dataset)):
        assert dataset[i]["ID"] == id_and_code_and_answer[i][0]

    print("存储")
    new_dataset=[]
    for i in range(len(dataset)):
        new_dataset.append({
            "ID": dataset[i]["ID"],
            "code": id_and_code_and_answer[i][1],
            "answer": id_and_code_and_answer[i][2]
        })
    with open(f'data/{file_name}.json', 'w', encoding='utf-8') as f:
        s = json.dumps(new_dataset, indent=4, ensure_ascii=False)
        f.write(s)

