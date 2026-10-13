from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def RAG(data):
    if data.endswith(".pdf"):
        loader = PyPDFLoader(data)

    elif data.endswith(".docx"):
        loader = Docx2txtLoader(data)

    else:
        print("Unsupported file type")
        return

    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )

    chunks = splitter.split_documents(documents)
    docs = PineconeVectorStore(
            index_name=config.PINECONE_INDEX,
            embedding=embeddings,
            pinecone_api_key=config.PINECONE_API_KEY
        )

    return docs


