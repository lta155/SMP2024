import pandas as pd
import re, json

from autogen import ConversableAgent
from pathlib import Path

import tempfile

from autogen import ConversableAgent
from autogen.coding import LocalCommandLineCodeExecutor
from prompt import CONVER_PROMPT
# Create a temporary directory to store the code files.
temp_dir = Path("./code")#tempfile.TemporaryDirectory()

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

with open('config.json', 'r') as f:
    config = json.load(f)
llm_config = get_llm_config(model_name, **config[model_name])




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
    timeout=30,  # Timeout for each code execution in seconds.
    work_dir=temp_dir.name,  # Use the temporary directory to store the code files.
)


# Create an agent with code executor configuration.
code_executor_agent = ConversableAgent(
    "code_executor_agent",
    llm_config=False,  # Turn off LLM for this agent.
    code_execution_config={"executor": executor},  # Use the local command line code executor.
    human_input_mode="NEVER",
    is_termination_msg=lambda msg: "TERMINATE" in msg.get("content", ""),
)


data_path = Path(config['data_path'])
df_test = pd.read_json(data_path / 'Final_TestSet/Final_TestSet.json').set_index("ID")
df_type = pd.read_json(data_path / 'Final_Example.json').set_index("ID")

template_cal = """The following is a problem of type "calculations". Your task is to think through the problem step by step, write the necessary code to solve it, execute the code, and extract the answer from the output.

    - If the problem explicitly requires a single numeric answer, your code must print this single numeric value.
    - If the problem explicitly requires multiple numeric answers, your code must print these values separated by commas.
    - If the problem requires a descriptive or analytic answer rather than a numeric one, your code must print the descriptive content before the answer.
    - For any numeric answers, if the values are decimals, they should be rounded to two decimal places.

Below is the problem content:

{}"""

template_tof = """The following is a problem of the type "True/False" Your task is to think through the problem step by step, write the necessary code to solve it, execute the code, and extract the answer from the output. 

    - The answer must be "TRUE" or "FALSE".
    - If the problem requires you to make multiple judgments, your code must print add 'specific question:' before the corresponding judgments.

Below is the problem content:

{}"""

template_draw = """The following is a problem of the type "draw" Your task is to think through the problem step by step, write the necessary code to complete the draw task.

Below is the problem content:

{}"""

template_tof_cal = """The following is a problem of type "multi(True/False, calculations)". Your task is to think through the problem step by step, write the necessary code to solve it, execute the code, and extract the answer from the output.

    - If the problem explicitly requires a single numeric answer, your code must print this single numeric value.
    - If the problem explicitly requires multiple numeric answers, your code must print these values separated by commas.
    - If the problem requires a descriptive or analytic answer rather than a numeric one, your code must print the descriptive content before the answer.
    - For any numeric answers, if the values are decimals, they should be rounded to two decimal places.
    - If the question asks you to make a judgment, you can reply by typing "TRUE" or "FALSE"

Below is the problem content:

{}"""

template_cal_draw = """The following is a problem of type "multi(calculations, draw)".Your task is to think through the problem step by step, write the necessary code to solve it, execute the code, and extract the answer from the output.
    - If the question asks you to draw a graph, complete the task as requested.
    - If the problem explicitly requires a single numeric answer, your code must print this single numeric value.
    - If the problem explicitly requires multiple numeric answers, your code must print these values separated by commas.
    - If the problem requires a descriptive or analytic answer rather than a numeric one, your code print the descriptive content before the answer.
    - For any numeric answers, if the values are decimals, they should be rounded to two decimal places.

Below is the problem content:

{}"""

template_tof_draw = """The following is a problem of type "multi(True/False, draw)".Your task is to think through the problem step by step, write the necessary code to solve it, execute the code, and extract the answer from the output.
    - If the problem asks you to make a judgment, you can reply by typing "TRUE" or "FALSE"
    - If the problem asks you to draw a graph, complete the task as requested.
    - If the question requires you to make multiple judgments, your code must print add specific descriptive content before the corresponding judgments.
    
Below is the problem content:

{}"""

d_template = {
    'calculations': template_cal,
    'True/False': template_tof,
    'draw': template_draw,
    'multi(True/False, calculations)': template_tof_cal,
    'multi(calculations, True/False)': template_tof_cal,
    'multi(calculations, draw)': template_cal_draw,
    'multi(draw, True/False)':template_tof_draw,
    'multi(True/False, draw)':template_tof_draw,
    }

if __name__ == '__main__':
    for i in range(22, 23):
        print('Problem: {}\n'.format(i))

        content = d_template[df_type.loc[i].problem_type].format(df_test.loc[i].question)
        filenames = extract_filenames(content)
        for filename in filenames:
            content = content.replace(filename, add_path(filename, data_path / 'Final_TestSet/data'))

        chat_result = code_executor_agent.initiate_chat(
            code_writer_agent,
            message=content,
            summary_method='reflection_with_llm',
            summary_args=dict(summary_prompt='only return the code output'),
        )

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