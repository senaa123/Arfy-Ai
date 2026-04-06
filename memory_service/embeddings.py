from sentence_transformers import SentenceTransformer

# Lightweight embedding model
_model = None

def get_embedding_model():
    """
    Load and return the sentence embedding model
    Uses lazy loading:
    - if model is not loaded yet, load it once
    - if already loaded, reuse the same model
    """
    global _model
    if _model is  None: 
        _model = SentenceTransformer("sentence-transformers/all-MiniLm-L6-v2")

    return _model

def embed_text(text: str):
    """
    Convert input text into a vector embedding.

    Steps:
    1. get the embedding model
    2. encode the text into a numeric vector
    3. convert the result to a normal Python list
    """
    model = get_embedding_model()
    # Encode text into embedding vector
    return model.encode(text).tolist()#convert numpy array to python