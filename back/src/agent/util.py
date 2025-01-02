from langchain_core.stores import BaseStore
from langchain_core.documents import Document
import os
from pathlib import Path
from typing import Generic, TypeVar

import ast
import json

from langchain_core.messages import BaseMessage
from langchain_core.load import load, dumpd

def json_read(file_path: str|Path):
    with open(file_path, "r", encoding="utf-8") as f:
        return my_loads(f.read())
def json_write(file_path: str|Path, data: object):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(my_dumps(data))

T = TypeVar("T")
class DiskStore(BaseStore[str, T], Generic[T]):

    def __init__(self, path:str, encoding:str="utf-8", index_fields:list[str]=[]):
        if not os.path.exists(path):
            os.makedirs(path)
        self.path = path
        self.encoding = encoding
        self.index_file = Path(self.path) / "__index__.json"
        if not self.index_file.exists():
            json_write(self.index_file, {})
        self.index_fields = index_fields
    def mget(self, keys) -> list[T]:
        return [json_read(Path(self.path) / key) for key in keys]

    def mset(self, key_value_pairs:list[tuple[str, T]]):
        for key, value in key_value_pairs:
            json_write(Path(self.path) / key, value)
            index_data = json_read(self.index_file)
            if self.index_fields:
                index_data[key] = {k: value[k] for k in self.index_fields}
            else:
                index_data[key] = {}
            json_write(self.index_file, index_data)

    def mdelete(self, keys):
        for key in keys:
            os.remove(Path(self.path) / key)
            index_data = json_read(self.index_file)
            del index_data[key]
            json_write(self.index_file, index_data)

    def yield_keys(self, prefix=None):
        if prefix is None:
            yield from os.listdir(self.path)
        else:
            for key in os.listdir(self.path):
                if key.startswith(prefix):
                    yield key

    def get_index(self):
        return json_read(self.index_file)
    
# class ModelDiskStore(DiskStore[T], Generic[T]):
#     def __init__(self, path:str, encoding:str="utf-8", index_fields:list[str]=[], model:Type[T]=BaseModel):
#         super().__init__(path, encoding, index_fields)
#         self.model = model

#     def mget(self, keys):
#         return [self.model(**json_read(Path(self.path) / key)) for key in keys]
    
class DocumentDiskStore(DiskStore[Document]):

    def mget(self, keys):
        for key in keys:
            with open(Path(self.path) / key, "r", encoding=self.encoding) as f:
                metadata = json.loads(f.readline())
                page_content = f.read()
                yield Document(page_content=page_content, **metadata)

    def mset(self, key_value_pairs:list[tuple[str, Document]]):
        for key, value in key_value_pairs:
            with open(Path(self.path) / key, "w", encoding=self.encoding) as f:
                metadata = {}
                for k, v in value.metadata.items():
                    if k != "page_content":
                        metadata[k] = v
                f.write(json.dumps(metadata))
                f.write("\n")
                f.write(value.page_content)
            index_data = json_read(self.index_file)
            index_data[key] = {k: v for k, v in value.metadata.items() if k in self.index_fields}
            json_write(self.index_file, index_data)



def my_exec(script, globals=None, locals=None):
    '''Execute a script and return the value of the last expression'''
    stmts = list(ast.iter_child_nodes(ast.parse(script)))
    if not stmts:
        return None
    if isinstance(stmts[-1], ast.Expr):
        # the last one is an expression and we will try to return the results
        # so we first execute the previous statements
        if len(stmts) > 1:
            exec(compile(ast.Module(body=stmts[:-1]), filename="<ast>", mode="exec"), globals, locals) # type: ignore
        # then we eval the last one
        return eval(compile(ast.Expression(body=stmts[-1].value), filename="<ast>", mode="eval"), globals, locals)
    else:
        # otherwise we just execute the entire code
        return exec(script, globals, locals)

def my_dumps(state):
    # vis = [] #detect circular reference
    # def custom_serializer(obj):
    #     try:
    #         if obj in vis:
    #             raise ValueError("Circular reference detected", vis)
    #         vis.append(obj)
    #         if isinstance(obj, BaseMessage):
    #             d = dumpd(obj)
    #             d['__dump_by_langchain'] = True
    #             return d
    #         else:
    #             return json.JSONEncoder().default(obj)
    #     except ValueError:
    #         print('======',obj)
    #         raise 

    class MyEncoder(json.JSONEncoder):  
        def default(self, obj):
            if isinstance(obj, BaseMessage):
                d = dumpd(obj)
                d['__dump_by_langchain'] = True
                return d
            return super().default(obj)

    return json.dumps(state,cls=MyEncoder,check_circular=False)

def my_loads(state):
    def custom_deserializer(obj):
        if isinstance(obj, dict) and '__dump_by_langchain' in obj:
            del obj['__dump_by_langchain']
            return load(obj)
        return obj

    return json.loads(state,object_hook=custom_deserializer)
