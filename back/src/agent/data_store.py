from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from .util import DiskStore
from langchain.retrievers import ParentDocumentRetriever
from pathlib import Path
from langchain_core.documents import Document


class SourceStore:
    '''
    '''
    def __init__(self, persist_directory: str):
        # This text splitter is used to create the child documents
        child_splitter = RecursiveCharacterTextSplitter(chunk_size=400)
        # The vectorstore to use to index the child chunks
        self.vector_store = Chroma(
            collection_name="chunks", embedding_function=OpenAIEmbeddings(), persist_directory="./data/chroma"
        )
        # The storage layer for the parent documents
        doc_store = DiskStore(str(Path(persist_directory) / "doc_store"))
        self.retriever = ParentDocumentRetriever(
            vectorstore=self.vector_store,
            docstore=doc_store,
            child_splitter=child_splitter,
        )

    def add_text_document(self, document: str):
        docs = Document(page_content=document)
        self.retriever.add_documents([docs])
