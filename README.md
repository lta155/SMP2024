# SMP 2024大模型图分析挑战赛
此项目为Robo Space团队在[SMP 2024大模型图分析挑战赛](https://tianchi.aliyun.com/competition/entrance/532253)复赛的解决方案。
## 代码结构
data: 存放数据集，可从该[页面](https://tianchi.aliyun.com/competition/entrance/532253/information)获取

tool: RAG工具

.env.tamplate: 环境变量模版

data_search.ipynb: 推理并生成答案

gpt4o.py: 初赛方案，复赛引用该脚本部分内容

main.py: 整合`data_search.ipynb`的结果并生成符合赛事要求的答案

prompt.py: 存放prompt

requirements.txt: 存放package
## 运行步骤
1. 创建环境并安装package
    ```bash
    conda create -n smp_graph python=3.10.14
    conda activate smp_graph
    pip install -r requirements.txt
    ```
2. 从[页面](https://tianchi.aliyun.com/competition/entrance/532253/information)获取数据集，将解压后的文档数据集放入data文件夹，由于gitHub不支持上传25MB文件所以Final_TestSet中的data并不是完整的数据集，因此需要让解压后的Final_TestSet替换原数据集。
3. 补全`.env.tamplate`中空缺的信息并重命名为`.env`
4. 运行`data_search.ipynb`文件进行推理
5. 运行`main.py`整合并输出推理结果