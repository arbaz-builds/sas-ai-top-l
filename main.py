from fastapi import FastAPI
from PIL import Image
from api import Navidia_embedding



app = FastAPI()


def image_fynction():
   image = Image.open('/content/.           Screenshot_2026_1010_191909.jpg').convert("RGB") 
   buf = io.BytesIO()
   image.save(buf, format="JPEG")
   data_url = "data:image/jpeg;base64," +         base64.b64encode(buf.getvalue()).decode()
   return data_url 



        docs = PineconeVectorStore(
            index_name=config.PINECONE_INDEX,
            embedding=embeddings,
            pinecone_api_key=config.PINECONE_API_KEY
        ).as_retriever(
            search_type="mmr",
            search_kwargs={"k": config.RETRIEVER_K, "fetch_k": config.RETRIEVER_FETCH_K, "lambda_mult": 0.7}
        ).invoke(query)

        return "".join(f"Source {i+1}:\n{d.page_content.strip()}\n\n" for i, d in enumerate(docs)) \
               or "No relevant content found."
    except Exception as e:
        return f"RAG error: {e}"




