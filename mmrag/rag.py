from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def RAG(data):
  if data  == pdf:
     text =  PyPDFLoader(data):
  else data  == doc:
     text = Docx2txtLoader(data)
     
  

splitter = RecursiveCharacterTextSplitter(
    chunk_size=100,
    chunk_overlap=20
)

chunks = splitter.split_text(text)

