# 读取res/GraphPro-master/doc datasets下的所有json文件
import asyncio
import importlib
import inspect
import json
import os
import pkgutil
import re
from typing import Any, Optional, Callable, List

import autogen
import dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.tools import StructuredTool
from langchain_openai import OpenAIEmbeddings
from pydantic.v1 import BaseModel, Field
from tqdm.asyncio import tqdm_asyncio

dotenv.load_dotenv()

def read_all_json_files(directory):
    dot_datasets={}
    # 遍历指定目录及其子目录下的所有文件
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                # 构建完整的文件路径
                file_path = os.path.join(root, file)
                # 打开并读取JSON文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"File: {file_path}")
                    dot_datasets[str(file)]=data  # 格式化输出JSON内容
    return dot_datasets


# 指定目录路径
directory = 'data/GraphPro-master/doc datasets'
def create_chunk():
    merged_dot_datasets=[]
    doc_datasets = read_all_json_files(directory)


    for file_name in doc_datasets.keys():
        package_name = re.findall(r'([a-zA-Z0-9_]+)\.json', file_name, re.DOTALL)[0]
        file_context_json = doc_datasets[file_name]

        # 每个文件分别处理，只提取需要的信息
        if file_name == "networkx.json":
            section_id_count = {}
            # 计算section id 需不需要合并
            for item in file_context_json:
                if "Section_id" in item:
                    section_id: str = item["Section_id"]
                elif 'Section ID' in item:
                    section_id: str = item['Section ID']
                else:
                    raise Exception("Section_id or Section ID not found")
                if section_id not in section_id_count:
                    section_id_count[section_id] = 0
                section_id_count[section_id] += 1

            section_id_merged = {}
            for item in file_context_json:
                if "Section_id" in item:
                    section_id: str = item["Section_id"]
                elif 'Section ID' in item:
                    section_id: str = item['Section ID']
                else:
                    raise Exception("Section_id or Section ID not found")

                # 如果此id只出现一次，或比较少次，那么没必要合并
                if section_id_count[section_id] <= 3:
                    info = {
                        "module": package_name,
                    }
                    info.update(item)
                    merged_dot_datasets.append(info)
                else:
                    # 合并，之后重新用
                    if section_id not in section_id_merged:
                        section_id_merged[section_id] = []
                    # 去掉里面的Section id 关键字把item字典转为元组列表
                    item = {k: v for k, v in item.items() if k != 'Section_id' and k != 'Section ID'}
                    section_id_merged[section_id].extend(tuple(item.items()))

            # 此时类已经聚合好了
            for section_id in section_id_merged.keys():
                # print(section_id, "已合并数量",section_id_count[section_id])

                temp_chunk = {}
                for item in section_id_merged[section_id]:
                    # print(item)
                    item_0, item_1 = item
                    # Description 要合并
                    if 'Description' in item_0 and type(item_1) is list:
                        item_1 = " ".join(item_1)

                    # 当遇到"Field List > Methods > Section ID"为元组第一个时候，进行分片
                    if item_0 == 'Field List > Methods > Section ID':
                        temp_chunk['Section_id'] = section_id
                        temp_chunk['module'] = package_name
                        merged_dot_datasets.append(temp_chunk)
                        temp_chunk = {}
                    temp_chunk[item_0] = item_1

        if file_name == "littleballoffur.json":
            # 这个文件比较整齐
            for item in file_context_json:
                section_id: str = item["Section_id"]
                info = {
                    "module": package_name,
                }
                info.update(item)
                merged_dot_datasets.append(info)

        if file_name == "karateclub.json":  # or file_name == "graspologic.json" :
            # 直接根据section_id合并
            temp_chunks = {}
            for item in file_context_json:
                section_id: str = item["Section_id"]
                if section_id not in temp_chunks:
                    temp_chunks[section_id] = {"module": package_name}
                temp_chunks[section_id].update(item)

            merged_dot_datasets.extend(list(temp_chunks.values()))

        if file_name == "graspologic.json" or file_name == "cdlib.json" or file_name == "igraph.json":
            section_id_count = {}
            # 计算section id 需不需要合并
            for item in file_context_json:
                if "Section_id" in item:
                    section_id: str = item["Section_id"]
                else:
                    raise Exception("Section_id or Section ID not found")
                if section_id not in section_id_count:
                    section_id_count[section_id] = 0
                section_id_count[section_id] += 1

            # 合并所有的section id
            section_id_merged = {}
            for item in file_context_json:
                section_id: str = item["Section_id"]

                if section_id not in section_id_merged:
                    section_id_merged[section_id] = {"module": package_name}
                section_id_merged[section_id].update(item)
            for section_id in section_id_merged.keys():
                # 如何section_id开头是小写，则直接作为chunk
                if section_id[0].islower():
                    merged_dot_datasets.append(section_id_merged[section_id])
                else:
                    # 如过是大写，那么。需要拆分为函数。
                    item = section_id_merged[section_id]
                    class_key = [i for i in item.keys() if
                                 (not re.match(r"Field List > Methods > [_A-Za-z].*", i, re.DOTALL)) or re.match(
                                     r"__init__.*", i, re.DOTALL)]
                    func_key = [i for i in item.keys() if re.match(r"Field List > Methods > [_A-Za-z].*", i, re.DOTALL)]

                    # 类,获取item（dict）里所有class_key（list）作为key的value
                    class_info = {k: v for k, v in item.items() if k in class_key}
                    class_info["module"] = package_name
                    class_info["Section_id"] = section_id
                    merged_dot_datasets.append(class_info)

                    # 函数,
                    for func in func_key:
                        func_info = {
                            "module": package_name,
                            "Section_id": section_id,
                            func: item[func],
                        }
                        merged_dot_datasets.append(func_info)
    return merged_dot_datasets



# 合并，只提取需要的信息，
def get_merged_dot_datasets():

    # 调用函数
    doc_datasets = read_all_json_files(directory)

    merged_dot_datasets = []
    for file_name in doc_datasets.keys():
        package_name = re.findall(r'([a-zA-Z0-9_]+)\.json', file_name, re.DOTALL)[0]
        file_context_json = doc_datasets[file_name]

        # 每个文件分别处理，只提取需要的信息
        if file_name == "networkx.json":
            # 获取函数，那么Section ID第一个字母必定是小写
            for item in file_context_json:
                if "Section_id" in item:
                    section_id: str = item["Section_id"]
                elif 'Section ID' in item:
                    section_id: str = item['Section ID']
                else:
                    raise Exception("Section_id or Section ID not found")

                if section_id[0].islower():
                    info = {
                        "module": package_name,
                        "function name": section_id,
                    }
                    info.update(item)
                    merged_dot_datasets.append(info)
                else:
                    continue
        elif file_name == "littleballoffur.json":
            # 这个文件比较整齐
            for item in file_context_json:
                section_id: str = item["Section_id"]
                info = {
                    "module": package_name,
                    "function name": section_id,
                }
                info.update(item)
                merged_dot_datasets.append(info)
        elif file_name == "cdlib.json" or file_name == "graspologic.json" or file_name == "igraph.json" or file_name == "karateclub.json":
            # 比较复杂，先合并，再筛选
            # merge
            merge = {}
            for item in file_context_json:
                section_id = item["Section_id"]
                if section_id not in merge.keys():
                    merge[section_id] = {}
                    merge[section_id].update(item)
                else:
                    merge[section_id].update(item)
            # 筛选，
            for item in merge.values():
                if item["Section_id"][0].islower():  # section_id 开头小写说明是函数
                    info = {
                        "module": package_name,
                        "function name": item["Section_id"],
                    }
                    info.update(item)
                    merged_dot_datasets.append(info)
                else:  # 开头大写，说明是类，应该抽取其中函数
                    for k in item.keys():
                        if re.match(r"Field List > Methods > [a-z]", k):
                            function_name = re.findall(r"Field List > Methods > ([a-z_]+)", k)[0]
                            info = {
                                "module": package_name,
                                "function name": function_name,
                                "Section_id": item["Section_id"],
                            }
                            info.update(item[k])
                            merged_dot_datasets.append(info)
    return merged_dot_datasets



embedding=OpenAIEmbeddings(
    model="text-embedding-3-large",
    api_key=os.getenv("BURN_HAIR_OPENAI_API_KEY_TEST"),#"QUEYU_OPENAI_API_KEY"),
    base_url=os.getenv("BURN_HAIR_URL")#"QUEYU_OPENAI_RUL")
)
local_path= "faiss_vectorstore"
try:
    vectorstore = FAISS.load_local(local_path, embedding, allow_dangerous_deserialization=True)
except Exception as e:
    print("初始化向量数据库")
    merged_dot_datasets = create_chunk()
    texts=[json.dumps(item) for item in merged_dot_datasets]
    vectorstore = FAISS.from_texts([texts[0]], embedding)
    async def add_texts_async(vectorstore, texts):
        for text in tqdm_asyncio(texts, desc="Adding texts",total=len(texts)):
            await vectorstore.aadd_texts([text])

    # Run the async function
    asyncio.run(add_texts_async(vectorstore, texts[1:]),)
    vectorstore.save_local(local_path)



faiss_vectorstore=vectorstore.as_retriever(k=5)


# def search_function_info(search_keywords:str):
#     text=faiss_vectorstore.invoke(search_keywords)[0].page_content
#     return text
# class SearchFunctionInfo(BaseModel):
#     search_keywords:str=Field(description="The keyword of function name and the package")
# function_searcher=StructuredTool.from_function(
#     func=search_function_info,
#     name="collect_function_info",
#     args_schema=SearchFunctionInfo,
#     description="collect function information",
# )

def search_documents_in_mutil_keywords(method_and_module_list:list,method_description:str= ""):
    res = []
    for mam in method_and_module_list:
        search_keywords = f"module:{mam['function_name']}, method:{mam['module_name']}, desc:{method_description}"

        module_name = mam['function_name'].lower().strip()
        method_name = mam['module_name'].strip().split(".")[-1]



        l = vectorstore.similarity_search_with_relevance_scores(search_keywords, k=10)
        for item in l:
            api_doc = item[0].page_content.lower()
            j=api_doc_json = json.loads(item[0].page_content)
            similarity_score = item[1]  # 相似度得分

            key_score = 0
            if j.get("Section_id", "").lower() == method_name.lower() \
                    or j.get("Section ID", "").lower() == method_name.lower() \
                    or "Field List > Methods > " + method_name in j.keys():
                if module_name == "" or (module_name != "" and j["module"].lower() in module_name):
                    key_score = 1

            res.append([api_doc_json, similarity_score, key_score])
    return sorted(res, key=lambda x: x[1]+x[2],reverse=True)


def search_documents(method_name:str="",module_name:str="",method_description:str= ""):
    module_name = module_name.lower().strip()
    method_name = method_name.strip().split(".")[-1]



    if method_name != "":
        res = []
        search_keywords = f"module:{module_name}, {method_name}, {method_description}"
        l=vectorstore.similarity_search(search_keywords, k=10)
        for item in l:
            # 取出符合要求函数
            j=json.loads(item.page_content)
            if j.get("Section_id","").lower() == method_name.lower() \
                    or j.get("Section ID","").lower() == method_name.lower() \
                    or "Field List > Methods > "+method_name in j.keys():
                if module_name=="" or (module_name!="" and j["module"].lower() in module_name):
                    res.append(item.page_content)
        if len(res)==0:
            return ["no method found"]
        else:
            return res
    elif method_description != "":
        search_keywords = f"module:{module_name}, {method_description}"
        if module_name == "":
            return [i.page_content for i in vectorstore.similarity_search(search_keywords, k=3)]
        else:
            l=vectorstore.similarity_search(search_keywords, k=3)
            res = []
            for item in l:
                if json.loads(item.page_content)["module"] == module_name:
                    res.append(item.page_content)
            if len(res) != 0:
                return res
        return ["no module found"]
    else:
        return ["no data found"]



from autogen.agentchat.contrib.vectordb.base import VectorDB, Document, ItemID, QueryResults


class MyVectorDB(VectorDB):

    active_collection: Any = None
    type: str = "MyVectorDB"
    embedding_function: Optional[Callable[[List[str]], List[List[float]]]] = (
        lambda text:embedding.embed_query(text)  # embeddings = embedding_function(sentences)
    )

    def create_collection(self, collection_name: str, overwrite: bool = False, get_or_create: bool = True) -> Any:
        """
        Create a collection in the vector database.
        Case 1. if the collection does not exist, create the collection.
        Case 2. the collection exists, if overwrite is True, it will overwrite the collection.
        Case 3. the collection exists and overwrite is False, if get_or_create is True, it will get the collection,
            otherwise it raise a ValueError.

        Args:
            collection_name: str | The name of the collection.
            overwrite: bool | Whether to overwrite the collection if it exists. Default is False.
            get_or_create: bool | Whether to get the collection if it exists. Default is True.

        Returns:
            Any | The collection object.
        """
        try:
            vectorstore = FAISS.load_local(local_path, embedding, allow_dangerous_deserialization=True)
        except Exception as e:
            print("初始化向量数据库")
            merged_dot_datasets = create_chunk()
            texts = [json.dumps(item) for item in merged_dot_datasets]
            vectorstore = FAISS.from_texts([texts[0]], embedding)

            async def add_texts_async(vectorstore, texts):
                for text in tqdm_asyncio(texts, desc="Adding texts", total=len(texts)):
                    await vectorstore.aadd_texts([text])

            # Run the async function
            asyncio.run(add_texts_async(vectorstore, texts[1:]), )
            vectorstore.save_local(local_path)
        return vectorstore

    def retrieve_docs(
        self,
        queries: List[str],
        collection_name: str = None,
        n_results: int = 10,
        distance_threshold: float = -1,
        **kwargs,
    ) -> QueryResults:
        """
        Retrieve documents from the collection of the vector database based on the queries.

        Args:
            queries: List[str] | A list of queries. Each query is a string.
            collection_name: str | The name of the collection. Default is None.
            n_results: int | The number of relevant documents to return. Default is 10.
            distance_threshold: float | The threshold for the distance score, only distance smaller than it will be
                returned. Don't filter with it if < 0. Default is -1.
            kwargs: Dict | Additional keyword arguments.

        Returns:
            QueryResults | The query results. Each query result is a list of list of tuples containing the document and
                the distance.
        """
        return [[(Document(id=1,content="doc1"), 0.1)]]


    def get_collection(self, collection_name: str = None) -> Any:
        """
        Get the collection from the vector database.

        Args:
            collection_name: str | The name of the collection. Default is None. If None, return the
                current active collection.

        Returns:
            Any | The collection object.
        """
        return self.active_collection

    def delete_collection(self, collection_name: str) -> Any:
        """
        Delete the collection from the vector database.

        Args:
            collection_name: str | The name of the collection.

        Returns:
            Any
        """
        self.active_collection=None

    def insert_docs(self, docs: List[Document], collection_name: str = None, upsert: bool = False, **kwargs) -> None:
        """
        Insert documents into the collection of the vector database.

        Args:
            docs: List[Document] | A list of documents. Each document is a TypedDict `Document`.
            collection_name: str | The name of the collection. Default is None.
            upsert: bool | Whether to update the document if it exists. Default is False.
            kwargs: Dict | Additional keyword arguments.

        Returns:
            None
        """
        pass

    def update_docs(self, docs: List[Document], collection_name: str = None, **kwargs) -> None:
        """
        Update documents in the collection of the vector database.

        Args:
            docs: List[Document] | A list of documents.
            collection_name: str | The name of the collection. Default is None.
            kwargs: Dict | Additional keyword arguments.

        Returns:
            None
        """
        pass

    def delete_docs(self, ids: List[ItemID], collection_name: str = None, **kwargs) -> None:
        """
        Delete documents from the collection of the vector database.

        Args:
            ids: List[ItemID] | A list of document ids. Each id is a typed `ItemID`.
            collection_name: str | The name of the collection. Default is None.
            kwargs: Dict | Additional keyword arguments.

        Returns:
            None
        """
        pass




    def get_docs_by_ids(
        self, ids: List[ItemID] = None, collection_name: str = None, include=None, **kwargs
    ) -> List[Document]:
        """
        Retrieve documents from the collection of the vector database based on the ids.

        Args:
            ids: List[ItemID] | A list of document ids. If None, will return all the documents. Default is None.
            collection_name: str | The name of the collection. Default is None.
            include: List[str] | The fields to include. Default is None.
                If None, will include ["metadatas", "documents"], ids will always be included. This may differ
                depending on the implementation.
            kwargs: dict | Additional keyword arguments.

        Returns:
            List[Document] | The results.
        """
        return []





