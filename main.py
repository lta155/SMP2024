import multiprocessing
import os

from autogen import Cache
import dotenv
from tqdm import tqdm

from gpt4o import *

dotenv.load_dotenv()

file_name="SMP_240915_answer_1"
# sign=True
def run(id_and_content: str):
    cache_seed = 1
    file_name = "SMP_240915_answer_1"
    ID, content = id_and_content.split("@####@")
    # agentops.init(auto_start_session=False)
    # agentops.start_session(tags=[file_name, "ID:"+ID])
    try:
        # Use DiskCache as cache
        with Cache.disk(cache_path_root="./autogen_cache", cache_seed=cache_seed) as cache:
            chat_result = code_executor_agent.initiate_chat(
                code_writer_agent,
                message=content,
                summary_method='reflection_with_llm',
                summary_args=dict(summary_prompt='only return the code output'),
                cache=cache,
                silent=True,
            )
        # agentops.end_session('Success')
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
        # agentops.end_session('Failure')
        print(f"Error processing item {ID}: {str(e)}")
        return ID+"@####@"+f"Error processing item {ID}: {str(e)}"

def run_concurrent(items):
    results = []
    try:
        with multiprocessing.Pool(processes=10) as pool:
            for result in tqdm(pool.imap_unordered(run, items), total=len(items)):
                if result is not None:
                    results.append(result)  # 仅记录成功的任务结果
                else:
                    print(f"Task failed.")
    except Exception as e:
        print(f"An error occurred during the concurrent execution: {e}")

    return results


if __name__ == "__main__":
    FROM,TO=0,512
    with open('data/Final_TestSet/Final_TestSet.json', 'r', encoding='utf-8') as f:
        dataset = json.load(f)[:]
    with open('data/id_and_content_0916_1.json', 'r', encoding='utf-8') as f:
        id_and_content = json.load(f)[:TO]
    # 判断文件存在
    if os.path.exists(f'data/{file_name}.json'):
        with open(f'data/{file_name}.json', 'r', encoding='utf-8') as f:
            answers=json.load(f)[:TO]
    else:
        answers=[]

    print("预处理")
    _id=[i["ID"] for i in answers if "answer" in i and i["answer"]!=""]
    id_and_content=[str(i["ID"] )+"@####@"+i["content"] for i in id_and_content if i["ID"] not in _id]

    print(f"运行,共{len(id_and_content)}")
    id_and_code_and_answer=run_concurrent(id_and_content)
    id_and_code_and_answer_json=[]
    for item in id_and_code_and_answer:
        tmp=item.split("@####@")
        if len(tmp)==3:
            id_and_code_and_answer_json.append({
                "ID": int(tmp[0]),
                "code": tmp[1],
                "answer": tmp[2]
            })
        else:
            id_and_code_and_answer_json.append({
                "ID": int(tmp[0]),
                "code": "",
                "answer": ""
            })
    id_and_code_and_answer_json=sorted(id_and_code_and_answer_json, key=lambda x: x["ID"], reverse=False)


    print("添加结果")
    final_answer=[]
    for dataset_item in dataset:
        tmp={"ID": dataset_item["ID"], "question":dataset_item["question"],"code":"","answer":""}
        for old_answer in answers:
            if old_answer["ID"]==dataset_item["ID"]:
                tmp["code"]=old_answer["code"]
                tmp["answer"]=old_answer["answer"]

        for new_answer in id_and_code_and_answer_json:
            if new_answer["ID"]==dataset_item["ID"]:
                tmp["code"]=new_answer["code"]
                tmp["answer"]=new_answer["answer"]
                print("update:",new_answer["ID"])
        final_answer.append(tmp)

    print("存储")
    with open(f'data/{file_name}.json', 'w', encoding='utf-8') as f:
        s = json.dumps(final_answer, indent=4, ensure_ascii=False)
        f.write(s)

