import json
import os
import re
from pathlib import Path
from typing import Annotated

import pandas as pd
from autogen import ConversableAgent
from autogen.coding import LocalCommandLineCodeExecutor


import dotenv
dotenv.load_dotenv()

# Create a temporary directory to store the code files.
temp_dir = Path("../code")#tempfile.TemporaryDirectory()

model_name = "gpt-4o"

def get_llm_config(model_name, base_url=None, port=None, api_key=None, temperature=1e-5, max_tokens=4096, 
                   cache_seed=None, seed=666):
    if base_url is not None and port is None:
        base_url = base_url
    elif base_url is None and port is not None:
        base_url = "http://localhost:{}/v1".format(port)
    llm_config = {
        "model": model_name,
        "base_url": base_url,
        "temperature": temperature,
        "cache_seed": cache_seed,
        "seed": seed,
    }
    if api_key is not None:
        llm_config["api_key"] = api_key
    if max_tokens is not None:
        llm_config["max_tokens"] = max_tokens
    return llm_config


def extract_filenames(text):
    pattern = r'\b\w+\.(dot|gml|sparse6)\b'
    matches = re.finditer(pattern, text)
    filenames = list(set([match.group(0) for match in matches]))
    return filenames


def add_path(filename: str, data_path: str) -> str:
    return str(Path(data_path) / filename)

def extract_python_code(text):
    pattern = r'```python(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    return [match.strip() for match in matches]


llm_config = get_llm_config(model_name,
                            api_key=os.getenv('API_KEY'),
                            base_url=os.getenv("BASE_URL"))


CONVER_PROMPT = """You are a helpful AI assistant.
Solve tasks using your coding and language skills.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    2. When you need to perform some task with code, use the code to perform the task and output the result. You can import the packages of 'cdlib', 'igraph', 'littleballoffur', 'graspologic', 'karateclub', and 'networkx'. Finish the task smartly.
    3. When you need to implement graph algorithms, you must use existing graph algorithm functions and cannot implement them yourself.
When generating code, you must pay attention to the following situations.
    1. When reading a file, do not use Python's built-in open function. Instead, use the function from the package mentioned in item 2 above, such as `nx.read_sparse6`.
    2. If the problem statement does not provide a file name but requires a graph for computation or analysis, please generate a graph that fits the context of the problem. Then, perform the required computation or analysis based on the entropy of the generated graph.
    3. You are allowed to install Python packages using pip, but you are prohibited from using Docker and any bash commands that might modify files, such as rm, mv, etc.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
When you find an answer, verify the answer carefully, make sure you answer all the questions as required. Include verifiable evidence in your response if possible.
Reply "TERMINATE" in the end when everything is done.
"""

code_writer_agent = ConversableAgent(
    "code_writer_agent",
    system_message=CONVER_PROMPT,
    llm_config=llm_config,
    code_execution_config=False,  # Turn off code execution for this agent.
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
)


# Create a local command line code executor.
executor = LocalCommandLineCodeExecutor(
    timeout=60*5,  # Timeout for each code execution in seconds.
    work_dir=temp_dir.name,  # Use the temporary directory to store the code files.
)




# Create an agent with code executor configuration.
code_executor_agent = ConversableAgent(
    "code_executor_agent",
    llm_config=False,#llm_config,  # Turn off LLM for this agent.
    system_message="You are a helpful AI Assistant. use tool to get api doc",
    code_execution_config={"executor": executor},  # Use the local command line code executor.
    human_input_mode="NEVER",
    is_termination_msg=lambda msg: "TERMINATE" in msg.get("content", ""),
)




template_cal = """The following is a problem of type "calculations". Your task is to think through the problem step by step, write the necessary code to solve it, execute the code, and extract the answer from the output.

    - If the problem explicitly requires a single numeric answer, your code must print this single numeric value.
    - If the problem explicitly requires multiple numeric answers, your code must print these values separated by commas.
    - If the problem requires a descriptive or analytic answer rather than a numeric one, your code must print the descriptive content before the answer.
    - For any numeric answers, if the values are decimals, they should be rounded to two decimal places.
    - Do not draw any images.Use print() function to output the results you need.

Below is the problem content:

{}"""

template_tof = """The following is a problem of the type "True/False" Your task is to think through the problem step by step, write the necessary code to solve it, execute the code, and extract the answer from the output. 

    - The answer must be "TRUE" or "FALSE".

Below is the problem content:

{}"""

template_draw = """The following is a problem of the type "draw" Your task is to think through the problem step by step, write the necessary code to complete the draw task.

    - If the problem requires you to draw an image, please include the code for drawing the image in the code.
    - The type of problem is "draw", so don't forget to add import matplotlib.pyplot as plt and plt.show() in the code.
Below is the problem content:

{}"""

template_tof_cal = """The following is a problem of type "multi(True/False, calculations)". Your task is to think through the problem step by step, write the necessary code to solve it, execute the code, and extract the answer from the output.

    - This problem requires you to make a judgment first, and then calculate a value based on the judgment result.
    - You must first make a judgment, then use the print function to output the content and result of your judgment, which will be True or False.
    - Then, based on the judgment result, calculate a value. You must use the print function to output the meaning and content of the result.
    - For any numeric answers, if the values are decimals, they should be rounded to two decimal places.
    - If the question asks you to make a judgment, you can reply by typing "TRUE" or "FALSE"

Below is the problem content:

{}"""

template_tof_draw = """The following is a problem of type "multi(True/False, draw)".Your task is to think through the problem step by step, write the necessary code to solve it, execute the code, and extract the answer from the output.
    - If the problem asks you to make a judgment, you can reply by typing "TRUE" or "FALSE"
    - If the problem asks you to draw a graph, complete the task as requested.
    - If the question requires you to make multiple judgments, your code must print add specific descriptive content before the corresponding judgments.

Below is the problem content:

{}"""

template_cal_draw = """The following is a problem of type "multi(calculations, draw)".Your task is to think through the problem step by step, write the necessary code to solve it, execute the code, and extract the answer from the output.
    - If the question asks you to draw a graph, complete the task as requested.
    - If the problem explicitly requires a single numeric answer, your code must print this single numeric value.
    - If the problem explicitly requires multiple numeric answers, your code must print these values separated by commas.
    - If the problem requires a descriptive or analytic answer rather than a numeric one, your code print the descriptive content before the answer.
    - For any numeric answers, if the values are decimals, they should be rounded to two decimal places.
    - The type of problem is "multi(calculations, draw)", so don't forget to add import matplotlib.pyplot as plt and plt.show() in the code.

Below is the problem content:

{}"""


# from autogen import register_function
# from tool.rag_tool import search_documents_by_help_function
# def query_document(package_name:Annotated[str, "python package name, it can only be 'cdlib' or 'igraph' or 'littleballoffur' or 'graspologic' or 'karateclub' or 'networkx' or '"],
#                    function_name:Annotated[str, "the name of the function or the method of the class to be queried, 'freeze'"])\
#         -> Annotated[str, "function or class document"]:
#     if package_name not in ['cdlib','igraph','littleballoffur','graspologic','karateclub','networkx']:
#         return "Invalid package name"
#     res = search_documents_by_help_function(function_name,package_name)
#     if res == "":
#         return "No document found"
#     return res
#
#
# register_function(
#     query_document,
#     caller=code_writer_agent,  # The assistant agent can suggest calls to the calculator.
#     executor=code_executor_agent,  # The user proxy agent can execute the calculator calls.
#     name="query_document",  # By default, the function name is used as the tool name.
#     description="You can look up the usage, parameters, examples, etc., of a function or a class method.",  # A description of the tool.
# )


d_template = {
    'calculations': template_cal,
    'True/False': template_tof,
    'draw': template_draw,
    'multi(True/False, calculations)': template_tof_cal, # ✅
    'multi(True/False, draw)': template_tof_draw, # ✅
    'multi(calculations, True/False)': template_tof_cal, # ✅
    'multi(calculations, draw)': template_cal_draw, # ✅ ❌
    'multi(draw, True/False)':template_tof_draw, # ✅
    }

if __name__ == '__main__':
    data_path = Path("./data")
    df_test = pd.read_json(data_path / 'Final_TestSet/Final_TestSet.json').set_index("ID")
    df_type = pd.read_json(data_path / 'Final_Example.json').set_index("ID")

    for i in range(385, 386):
        print('Problem: {}\n'.format(i))

        content = d_template[df_type.loc[i].problem_type].format(df_test.loc[i].question)
        print(content)
        filenames = extract_filenames(content)
        for filename in filenames:
            content = content.replace(filename, add_path(filename, data_path / 'Final_TestSet/data'))

        chat_result = code_executor_agent.initiate_chat(
            code_writer_agent,
            message=content,
            summary_method='reflection_with_llm',
            summary_args=dict(summary_prompt='only return the code output'),
        )
        print(chat_result.summary)
        full_res_path = Path('./full_results/') / 'stage1' / model_name
        full_res_path.mkdir(parents=True, exist_ok=True)
        with open(full_res_path / '{}.json'.format(i), 'w') as f:
            json.dump(chat_result.chat_history, f, indent=4)
        res_path = Path('./results/') / 'stage1'
        res_path.mkdir(parents=True, exist_ok=True)
        with open(res_path / '{}.jsonl'.format(model_name), 'a') as f:
            answer = chat_result.summary
            if isinstance(answer, dict):
                answer = answer['content']
            code = extract_python_code(chat_result.chat_history[-3]['content'])[-1]
            json.dump({'id': i, 'answer': answer, 'code': code}, f)
            f.write('\n')