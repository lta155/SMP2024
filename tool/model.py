import re
from functools import reduce

import os
import re
from functools import reduce
from typing import List, Optional, Any

import dotenv
import requests
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from openai import OpenAI
from typing_extensions import override

dotenv.load_dotenv()




gpt4o=ChatOpenAI(
    api_key=os.getenv("WLAI_API_KEY"),
    base_url=os.getenv("WLAI_BASE_URL"),
    model="gpt-4o-2024-08-06",
    temperature=0.0,
)

class CodeOutputParser(StrOutputParser):
    def parse(self, text: str) -> str:
        code=reduce(lambda a,b:a+"\n\n"+b,re.findall(r'```python(.*?)```', text, re.DOTALL))
        return code

class BooleanOutputParser(StrOutputParser):
    def parse(self, text: str) -> bool:
        return bool(re.search(r"(True)", text, re.IGNORECASE))


def prompt123(input:dict):
    question=input["question"]
    question_type=input["question_type"]
    prompt=ChatPromptTemplate.from_messages([
    ("system","根据任务，简洁的输出任务目标，{out_type}"),
    ("human","""
task：任务说明
goal：简短的最终任务目标

task：{question}
goal：
""")
    ])
    if question_type== "calculations":
        return prompt.invoke({"question":question,"out_type":""})
    elif question_type== "True/False":
        return prompt.invoke({"question":question,"out_type":"输出结果只能是True或False"})
    else:
        raise Exception("unknown question_type")

goal_runnable=RunnableLambda(prompt123) | gpt4o | StrOutputParser()


extract_prompt=ChatPromptTemplate.from_messages([
    ("system","你是一个实体提取器，仅能提取文本中实体的，你任务提取出文本中的python函数和python库"),
    ("human","""
你是一个实体提取器，仅能提取文本中实体的，你任务提取出文本中的图分析相关的python函数和python库，以Json格式返回。函数和库必须是文本中有出现的明确使用的，不是只有描述没有具体名字的，且肯定是英文，并且是图算法相关的，不是载入/绘图/输出等。如果没有函数和库，直接返回空字符串。
返回的json格式：
```json
{{"function_name":"","module_name":""}}
```

<example>
TEXT: 
想象一下，你遇到了一份详细的 .dot 文件，这份文件就像一张藏宝图，揭示了珍贵珠宝收藏中的复杂关系和联系。这张地图就是“JewelRelations.dot”，其中充满了关于各种珠宝之间互动和接触点的数据。为了评估甚至提升这个收藏的价值，你希望将这些信息从这个 dot 文件转移到一个更易处理的结构中。你会如何优雅地将“JewelRelations.dot”中的数据转置到 NetworkX 的 MultiGraph 或 Graph 对象中？这一战略举措将使你能够以珠宝鉴定师的精湛技艺来操作和探索这些联系。
OUTPUT: 
{{"function_name":"","module_name":""}}
</example>

<example>
TEXT: 
为了更好地跟踪和分析我们社区内的情感变化，可以考虑使用“运行平均值”的概念。想象我们有一个象征性的“情感计”，我们决定在其中记录20的值十次，代表一致的正面输入。在每次输入后，我们将计算当前的平均情感（平均值）和情感变化范围（标准差），以了解集体情感的变化。你能演示如何使用igraph库中的RunningMean.add函数将20添加十次并获得当前的平均值和标准差吗？
OUTPUT: 
 {{"function_name":"RunningMean.add","module_name":"igraph"}}
</example>

<example>
TEXT:
作为一名网络分析师，你的任务是分析大都市中交通网络的影响和有效性。你有一个包含城市中各个社区之间道路连接信息的数据集。该数据集包括边集[(0, 1), (1, 2), (2, 3), (3, 4), (1, 4)]，表示不同社区之间的道路连接。\n\n你的任务是使用NetworkX库计算从特定社区（对应于ID=1的顶点）到所有其他社区的最短路径，以评估城市交通选项的效率。你将通过利用NetworkX库提供的get_shortest_paths方法来分析城市内不同社区的连通性和可达性。
OUTPUT:
{{'function_name': 'get_shortest_paths', 'module_name': 'NetworkX'}}
</example>

<example>
TEXT:
想象一下，你正在监督一个项目，试图对齐两个公园的设计：公园A，形状像一个简单的环，有四个检查点；公园B，设计成一个中央枢纽的风格，有五条辐条通向不同的检查点。你的任务是以最有效的方式重新组织公园A，以镜像公园B的布局，就所需的更改而言。在这种情况下，你将使用一个类似于NetworkX的“optimal_edit_paths”函数的复杂规划工具来确定所有将公园A的布局转变为与公园B相同的设计所需的最少修改序列。你能估计一下这些修改序列的总数以及最有效的转换计划的成本吗？
OUTPUT:
{{'function_name': 'optimal_edit_paths', 'module_name': 'NetworkX'}}
</example>

TEXT: {text}"""),
],)
extract_runnable= extract_prompt | gpt4o | JsonOutputParser()

extract_graph_algorithm_prompt=ChatPromptTemplate.from_messages([
    ("system","You are a graph Algorithm Extractor that faithfully extracts descriptions of graph algorithms mentioned in text"),
    ("human","""{text}""")
])
extract_graph_algorithm_runnable=extract_graph_algorithm_prompt|gpt4o|StrOutputParser()


generating_code_prompt=ChatPromptTemplate.from_messages([
    ("system","你是一个图算法专家助手，擅长执行图算法任务，在一个代码快里编写完整的可运行的python代码，此print函数输出问题答案并保留2位有效数字，不能绘制任何图片，代码尽可能精简，生成的例子需要尽可能简单。"),
    ("human","""{question}"""),
])
generating_code_runnable=generating_code_prompt|gpt4o|CodeOutputParser()


translate_prompt=ChatPromptTemplate.from_messages([
    ("system","You are a professional, authentic machine translation engine."),
    ("human","""Translate the following source text to Chinese, Output translation directly without any additional text.
Source Text: {text}
Translated Text:""")
])
translation_runnable= translate_prompt | gpt4o | StrOutputParser()

fix_code_prompt=ChatPromptTemplate.from_messages([
    ("system","You are a professional, authentic code fixer. 你是一个图算法专家助手，擅长执行图算法任务，在一个代码快里编写完整的可运行的python代码，此print函数输出问题答案并保留2位有效数字，不能绘制任何图片，不能用任何显示进度的工具如tqdm，代码尽可能精简，生成的例子需要尽可能简单。"),
    ("human","""
<Question>
{question}
<\Question>

<infos>
{rag_infos}
<\infos>

<code>
{code}
<\code>

<errors>
{errors}
<\errors>

fix code""")
],)
fix_code_runnable= fix_code_prompt | gpt4o.bind(temperature=0.4) | CodeOutputParser()

judge_prompt = ChatPromptTemplate.from_messages([
    ("system","你是一个领导，只会返回True或False，判断是否满足目标，目标由goal给出，代码由code给出，标准输出由stdout给出，你判断任务有么有完成，最后返回True或False"),
    ("human","""
<Question>
{question}
</Question>

<goal>
{goal}
</goal>

<code>
{code}
</code>

<code_std_output>
{stdout}
</code_std_output>

It returns True if the goal is reached and False otherwise.
""")
])
judge_runnable_bool= judge_prompt | gpt4o | BooleanOutputParser()
judge_runnable_text= judge_prompt | gpt4o | StrOutputParser()



