from langchain.tools import tool as langchain_tool
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.tools import BaseTool
from typing import Union, Callable, Optional, Type, Literal
from langchain_core.runnables import Runnable
from .data_store import SourceStore
from .util import my_exec

def tool(
    *args: Union[str, Callable, Runnable],
    return_direct: bool = False,
    args_schema: Optional[Type] = None,
    infer_schema: bool = True,
    response_format: Literal["content", "content_and_artifact"] = "content",
    parse_docstring: bool = False,
    error_on_invalid_docstring: bool = True,
) -> Callable[[Callable], BaseTool]:
    return langchain_tool(
        *args,
        return_direct=return_direct,
        args_schema=args_schema,
        infer_schema=infer_schema,
        response_format=response_format,
        parse_docstring=parse_docstring,
        error_on_invalid_docstring=error_on_invalid_docstring,
    )

@tool(response_format="content_and_artifact")
def get_website_content(url: str):
    """Get the content of a website"""
    loader = WebBaseLoader(web_paths=(url,))
    docs = loader.load()
    return docs[0].page_content, docs

# @tool(response_format="content_and_artifact")
# def retrieve(query: str):
#     """Retrieve information related to a query from the database"""
#     retrieved_docs = vector_store.similarity_search(query, k=2)
#     serialized = "\n\n".join(
#         (f"Source: {doc.metadata}\n" f"Content: {doc.page_content}")
#         for doc in retrieved_docs
#     )
#     return serialized, retrieved_docs

class LongTermMemory(BaseTool):
    data_store: SourceStore
    name: str = "get_long_term_memory"
    description: str = """
    You have a long term memory. Recall what you have learned from the past.
    """

    def _run(self, query: str):
        retrieved_docs = self.data_store.retriever.get_relevant_documents(query)
        serialized = "\n\n".join(
            (f"Source: {doc.metadata}\n" f"Content: {doc.page_content}")
            for doc in retrieved_docs
        )
        if len(retrieved_docs) == 0:
            return "No information found in the memory. If you think it can be found in internet, try using the get_website_content as alternative."
        return serialized, retrieved_docs
    
class Memorize(BaseTool):
    data_store: SourceStore
    name: str = "memorize"
    description: str = """
    Whenever you encounter information that you think is important, the best thing to do is to learn and remember it.
    All the memory will be stored in your long term memory and can be acessed with long_term_memory in the future.
    Use this tool frequently so you can be more and more smarter in the future.
    """

    def _run(self, memory: str):
        self.data_store.add_memory(memory)

@tool(response_format="content")
def execute_python_code(query: str):
    """Execute a python code.
    If you find you have no ability to do something with other tools, just use this tool to do it.
    You have all the power to do anything with the execute tool !.
    """
    from io import StringIO
    from contextlib import redirect_stdout
    import traceback
    
    f = StringIO()
    with redirect_stdout(f):
        try:
            ret = my_exec(query)
        except Exception:
            error_stringio = StringIO()
            traceback.print_exc(file=error_stringio)
            return {"code": query, "result": f.getvalue(), "error": error_stringio.getvalue(), "status": "error"}
    
    output = f.getvalue()
    if output != '':
       output = output + "\n" + str(ret)
    else:
        output = str(ret)
    return {"code": query, "result": output, "status": "success"}
    
@tool(response_format='content')
def read_file(file_path: str) -> str:
    '''Read the contents of a file in the local computer.'''
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        return str(e)