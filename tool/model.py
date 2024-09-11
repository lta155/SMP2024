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
    model="gpt-4o",
    temperature=0.3,
)


tof_prompt=ChatPromptTemplate.from_messages([
            ("system", "你是一个图算法专家，你需要从下面的任务描述中，提取出任务的最终目标，这通常是一个判断，返回True或False。\n1. 使用用英文。2.使用第一人称。3.一句话转述。4.print回答和判断。"), # 指令
            ("user", """
<example>
input:
Imagine we're constructing a new activity scheduling system for our community rehabilitation center, aimed at promoting social interaction for our clients through various group activities. The activities are represented by nodes, and the direct pairwise overlaps in schedulingdue to shared participants or resourcesare represented by edges between them. Our current activity network is comprised of the following connections: [(0, 1), (0, 2), (1, 2), (1, 3), (1, 4), (4, 5), (3, 6), (5, 7), (3, 8), (5, 9), (3, 10)].
output:
Does the graph maintain the AT-free property? print("the graph maintain the AT-free property："+"True" if var else "False")
<example>

<example>
input:
Imagine we have a community network structured like an icosahedral shape, where each point or node represents a family, and the lines connecting these families are their direct relationships. Now, let's consider two families in this network that are not directly connected. We want to ensure that there are multiple lines of support between these two families using other connected families as intermediaries, so that if one line of support is unavailable, others can be used without overburdening any single family. Could you tell me, in this kind of community network, how many separate or independent support pathways we could establish between any two families that do not have a direct connection? It's important to note that no single intermediary family should be a part of more than one pathway to ensure we're distributing the support network evenly without causing strain on any particular family.
output:
Can multiple independent support pathways be established between two families that do not have a direct connection? print("the graph have a direct connection："+"True" if var else "False")
<example>

<example>
input:
Use the siblinarity_antichain method to perform community detection on the above network graph, with the Lambda parameter set to 2. Calculate and print the size of each detected sub-community (or 'antichain').This information will help you better analyze and investigate the interaction patterns of these individuals to uncover potential fraudulent activities.
output:
Is this graph a directed acyclic graph? print(f"directed acyclic graph："+"True" if var else "False")
<example>

<example>
input:
To ensure that the course scheduling is efficient and meets certain regulatory standards, you are required to evaluate the complexity of the network. Specifically, you need to determine the 'treewidth' of this network, considering it as a chordal graph to facilitate your inspection process. This metric will help you understand the minimum level of connectedness that ensures no course is over-scheduled or under-scheduled due to the way the network is structured.
output:
Is this graph a chordal graph? print(f"chordal graph :"+"True" if var else "False")
<example>

input:
{question}
output:
""")])

cal_prompt=ChatPromptTemplate.from_messages([
            ("system", "你是一个图算法专家，你需要从下面的任务描述中，提取出任务的最终目标，这通常是一或多个图算法相关的指标。\n1. 使用用英文。2.使用第一人称。3.一句话转述。4.指出结果类型"), # 指令
            ("user", """
input:
{question}
output:
""")])

draw_prompt=ChatPromptTemplate.from_messages([
            ("system", "你是一个图算法专家，你需要从下面的任务描述中，提取出任务的最终目标，这通常是需要绘制一张图算法相关的图片。\n1. 使用用英文。2.使用第一人称。3.一句话转述。4.指出结果类型"), # 指令
            ("user", """
input:
{question}
output:
""")])


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

mutil_extract_prompt=ChatPromptTemplate.from_messages([
    ("system","""
你是一个图算法提取器，你的任务是从文本中准确提取出图算法有关的python函数/python库/图算法指标，斌遵循一下规则：
1. 以json格式返回，返回的json格式：
```json
{{"function_name":"","module_name":"","graph algorithm metrics",""}}
```
    """),
    ("human","""
<example>
TEXT: 
想象一下，你遇到了一份详细的 .dot 文件，这份文件就像一张藏宝图，揭示了珍贵珠宝收藏中的复杂关系和联系。这张地图就是“JewelRelations.dot”，其中充满了关于各种珠宝之间互动和接触点的数据。为了评估甚至提升这个收藏的价值，你希望将这些信息从这个 dot 文件转移到一个更易处理的结构中。你会如何优雅地将“JewelRelations.dot”中的数据转置到 NetworkX 的 MultiGraph 或 Graph 对象中？这一战略举措将使你能够以珠宝鉴定师的精湛技艺来操作和探索这些联系。
OUTPUT: 
{{"function_name":"","module_name":"","algorithm metrics",""}}
</example>

<example>
TEXT: 
为了更好地跟踪和分析我们社区内的情感变化，可以考虑使用“运行平均值”的概念。想象我们有一个象征性的“情感计”，我们决定在其中记录20的值十次，代表一致的正面输入。在每次输入后，我们将计算当前的平均情感（平均值）和情感变化范围（标准差），以了解集体情感的变化。你能演示如何使用igraph库中的RunningMean.add函数将20添加十次并获得当前的平均值和标准差吗？
OUTPUT: 
 {{"function_name":"RunningMean.add","module_name":"igraph","algorithm metrics","使用igraph库中的RunningMean.add函数将20添加十次并获得当前的平均值和标准差"}}
</example>

<example>
TEXT:
作为一名网络分析师，你的任务是分析大都市中交通网络的影响和有效性。你有一个包含城市中各个社区之间道路连接信息的数据集。该数据集包括边集[(0, 1), (1, 2), (2, 3), (3, 4), (1, 4)]，表示不同社区之间的道路连接。\n\n你的任务是使用NetworkX库计算从特定社区（对应于ID=1的顶点）到所有其他社区的最短路径，以评估城市交通选项的效率。你将通过利用NetworkX库提供的get_shortest_paths方法来分析城市内不同社区的连通性和可达性。
OUTPUT:
{{'function_name': 'get_shortest_paths', 'module_name': 'NetworkX',"algorithm metrics","连通性和可达性"}}
</example>


    """),
])

extract_prompt=ChatPromptTemplate.from_messages([
    ("system","你是一个实体提取器，仅能提取文本中实体的，你任务提取出文本中的python函数和python库"),
    ("human","""
你是一个实体提取器，仅能提取文本中实体的，你任务提取出文本中的图分析相关的python函数和python库，以Json格式返回。函数和库必须是文本中有出现的明确使用的，不是只有描述没有具体名字的，且肯定是英文，并且是图算法相关的，不是载入/绘图/输出等。如果没有函数和库，直接返回空字符串。
返回的jsonl格式：
```json
[{{"function_name":"","module_name":""}}]
```

<example>
TEXT: 
想象一下，你遇到了一份详细的 .dot 文件，这份文件就像一张藏宝图，揭示了珍贵珠宝收藏中的复杂关系和联系。这张地图就是“JewelRelations.dot”，其中充满了关于各种珠宝之间互动和接触点的数据。为了评估甚至提升这个收藏的价值，你希望将这些信息从这个 dot 文件转移到一个更易处理的结构中。你会如何优雅地将“JewelRelations.dot”中的数据转置到 NetworkX 的 MultiGraph 或 Graph 对象中？这一战略举措将使你能够以珠宝鉴定师的精湛技艺来操作和探索这些联系。
OUTPUT: 
[{{"function_name":"","module_name":""}}]
</example>

<example>
TEXT: 
为了更好地跟踪和分析我们社区内的情感变化，可以考虑使用“运行平均值”的概念。想象我们有一个象征性的“情感计”，我们决定在其中记录20的值十次，代表一致的正面输入。在每次输入后，我们将计算当前的平均情感（平均值）和情感变化范围（标准差），以了解集体情感的变化。你能演示如何使用igraph库中的RunningMean.add函数将20添加十次并获得当前的平均值和标准差吗？
OUTPUT: 
 [{{"function_name":"RunningMean.add","module_name":"igraph"}}]
</example>

<example>
TEXT:
作为一名网络分析师，你的任务是分析大都市中交通网络的影响和有效性。你有一个包含城市中各个社区之间道路连接信息的数据集。该数据集包括边集[(0, 1), (1, 2), (2, 3), (3, 4), (1, 4)]，表示不同社区之间的道路连接。\n\n你的任务是使用NetworkX库计算从特定社区（对应于ID=1的顶点）到所有其他社区的最短路径，以评估城市交通选项的效率。你将通过利用NetworkX库提供的get_shortest_paths方法来分析城市内不同社区的连通性和可达性。
OUTPUT:
[{{'function_name': 'get_shortest_paths', 'module_name': 'NetworkX'}}]
</example>

<example>
TEXT:
想象一下，你正在监督一个项目，试图对齐两个公园的设计：公园A，形状像一个简单的环，有四个检查点；公园B，设计成一个中央枢纽的风格，有五条辐条通向不同的检查点。你的任务是以最有效的方式重新组织公园A，以镜像公园B的布局，就所需的更改而言。在这种情况下，你将使用一个类似于NetworkX的“optimal_edit_paths”函数的复杂规划工具来确定所有将公园A的布局转变为与公园B相同的设计所需的最少修改序列。你能估计一下这些修改序列的总数以及最有效的转换计划的成本吗？
OUTPUT:
[{{'function_name': 'optimal_edit_paths', 'module_name': 'NetworkX'}}]
</example>

<example>
TEXT:
作为一名负责培养这个社区精神福祉的牧师，你需要辨别这些联系的底层结构。为了有效地做到这一点，你将进行类似于使用igraph包中的community_multilevel方法的过程，从而揭示这个无向图中多层次的连接。此外，为了提供一个反映家族谱系中树状层级或会众分支扩展的视觉表示，你可能会使用同一个igraph工具包中的layout_reingold_tilford函数，以一种反映其成员之间自然流动和关系的方式来排列这个网络。
OUTPUT:
[{{'function_name': 'community_multilevel', 'module_name': 'igraph'}},{{'function_name': 'layout_reingold_tilford', 'module_name': 'igraph'}}]
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



