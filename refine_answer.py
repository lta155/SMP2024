import json

def read_jsonl(file_path):
    data_list = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            data_list.append(json.loads(line.strip()))
    return data_list

file_path = 'results/stage1/gpt-4o.jsonl'
data = read_jsonl(file_path)

with open("res_Preliminary/Preliminary_TestSet/Preliminary_TestSet.json", "r", encoding="utf-8") as file:
    file = file.read()
    temp = json.loads(file)

for i in range(100):
    temp[i]["answer"] = data[i]["answer"]
for i in range(100, 1000):
    temp[i]["answer"] = ""
with open("result.json", "w", encoding="utf-8") as file:
    json.dump(temp, file, ensure_ascii=False, indent=4)