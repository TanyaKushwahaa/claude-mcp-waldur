# src/tools/retrieve_api_endpoint.py

"""
This module defines an MCP tool to find the most relevant Waldur API endpoint
for a given short, action-oriented query. 

It works by:
1. Loading the Waldur OpenAPI schema (from cache or URL).
2. Processing each endpoint into text chunks suitable for embedding.
3. Embedding endpoints using a SentenceTransformer model.
4. Performing semantic search using FAISS to find the top matching endpoints.
5. Filtering results by HTTP method and target entity.

Embeddings and FAISS index are cached locally in './cache' for efficiency.
"""
from sentence_transformers import SentenceTransformer
from typing import Dict, List
import requests
import yaml
import os
import numpy as np
import pickle
import faiss # type: ignore
import asyncio
from mcp_instance import mcp

from utils import normalise_waldur_token

model = None
cache_dir = "./cache"
index = None
chunks = []
embedded_chunks = []

def init_cache_dir():
    """Initialises the cache directory for storing the model and YAML file."""
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

def load_model(model_name="BAAI/bge-large-en-v1.5", cache_dir=cache_dir):
    """Loads the SentenceTransformer model."""
    global model
    if model is None:
        model = SentenceTransformer(model_name, cache_folder=cache_dir)
    return model

def embed_text(text: str) -> np.ndarray:
    """Embeds the text using the SentenceTransformer model."""
    global model
    if model is None:
        model = load_model()
    return model.encode(text, normalize_embeddings=True, convert_to_numpy=True)

def process_api_schema(api_schema: Dict) -> List[Dict]:
    """Processes the OpenAPI schema and splits it into embedding-ready chunks."""
    result_chunks = []

    if "paths" not in api_schema:
        return result_chunks

    for path, methods in api_schema["paths"].items():
        for method, method_details in methods.items():
            if method not in ["get", "post", "put", "delete", "patch"]:
                continue

            summary = method_details.get("summary", "")
            description = method_details.get("description", "")
            parameters = method_details.get("parameters", [])

            # Extract entity from the path
            path_parts = path.strip("/").split("/")
            entity_hint = path_parts[1] if len(path_parts) > 1 else ""
            
            # Intent keywords
            intent_keywords = {
                "post": "create add new insert register assign link provision",
                "put": "update modify replace edit overwrite",
                "patch": "update modify partial change adjust",
                "delete": "remove delete destroy unlink detach",
                "get": "retrieve get fetch list read show search",
            }
            method_keywords = intent_keywords.get(method.lower(), "")

            # Collect parameter texts
            param_texts = [
                f"param: {param.get('name', '')} — {param.get('description', '')}"
                for param in parameters
            ]

            # Combine all text fields for embedding
            embedding_text = (
                f"{method.upper()} {path} {summary} {description} "
                f"{' '.join(param_texts)} "
                f"Entity: {entity_hint} "
                f"Intent: {method_keywords}"
            ).strip()

            # Build the chunk
            chunk = {
                "path": path,
                "method": method.upper(),
                "summary": summary,
                "description": description,
                "parameters": parameters,
                "text_for_embedding": embedding_text,
            }
            result_chunks.append(chunk)
    return result_chunks

def load_api_schema(url="https://docs.waldur.com/latest/API/waldur-openapi-schema.yaml") -> Dict:
    """Loads the OpenAPI schema from URL or cache."""
    global chunks
    cache_file = f"{cache_dir}/waldur-openapi-schema.yaml"
    
    # Load from cache if available
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            try:
                api_schema = yaml.safe_load(f)
            except Exception as e:
                print(f"Error loading cached schema: {e}")

    # If cache is not available, download and cache it
    else:
        response = requests.get(url)
        api_schema = yaml.safe_load(response.text)
        # Cache the schema
        with open(cache_file, "w") as f:  
            yaml.dump(api_schema, f)

    chunks = process_api_schema(api_schema)
    return chunks



async def retrieve_relevant_apis(query:str, k:int) -> List[Dict]:
    """
    Retrieves the top k relevant API chunks using FAISS semantic search.
    
    Args:
        query: Search query describing desired API action.
        k: Number of results to return.

    Returns:
        List of top k relevant API chunks.
    """
    global chunks, embedded_chunks, index

    if len(chunks) == 0:
        chunks = load_api_schema()

    # Check if index file and embedded chunks are in cache
    embedded_chunks_file = f"{cache_dir}/embedded_chunks.pkl"
    index_file = f"{cache_dir}/faiss_index.bin"

    if os.path.exists(embedded_chunks_file) and os.path.exists(index_file):
        index = faiss.read_index(index_file)
        with open(embedded_chunks_file, "rb") as f:
            embedded_chunks = pickle.load(f)
        
    else:
        # Converting text to embedding using the embed_text function
        embedded_chunks = [
            {
                "chunk": chunk,
                "embedding": embed_text(chunk["text_for_embedding"])
        } 
                for chunk in chunks
    ] 

        # Save the index and embedded chunks to cache
        with open(embedded_chunks_file, "wb") as f:
            pickle.dump(embedded_chunks, f)

        dimension = len(embedded_chunks[0]['embedding'])
        embeddings = np.array([ec["embedding"] for ec in embedded_chunks])
        
        # Initialise the index
        index = faiss.IndexFlatL2(dimension) 
        # Add the embeddings to the index
        index.add(embeddings) 
        # Save the index to cache
        faiss.write_index(index, index_file)

    # Search the index
    loop = asyncio.get_running_loop() # This moves the embedding function to the event loop which means shifting this heavy computation to a different thread
    # None parameter is used to indicate that it should use the default executor, which is typically a thread pool executor.
    query_vec = await loop.run_in_executor(
        None, 
        lambda:np.array([embed_text(query)], dtype = np.float32)
    ) # loop.run_in_executor is used to run a function in a different thread or process, allowing for concurrent execution of tasks.
    distances, indices = index.search(query_vec, k)

    results = []
    # indices appear as a nested list: [[0 1 2 3 4]] that's why we use indices[0]
    for i, idx in enumerate(indices[0]):
        if idx != -1: # idx is -1 if no match found
            chunk = embedded_chunks[idx]["chunk"]
            result = {
                "path" : chunk["path"],
                "method" : chunk["method"],
                "description" : chunk["description"],
                "score" : float(distances[0][i]),
            }
            results.append(result)
    return results

def post_filter_results(results, method, target_entity, max_results=10):
    """
    Filters Waldur OpenAPI endpoints by method and entity.

    Args:
        results: List of dicts with 'path', 'method', 'description', 'score'
        method (str): Desired HTTP method, e.g., 'GET', 'POST', 'PUT', etc.
        target_entity (str): Target entity like 'customer', 'project', etc.
        max_results (int): Max number of results to return

    Returns:
        Filtered and sorted list of endpoints
    """

    relevant_apis = []
    method = method.lower()
    target_entity = target_entity.lower()

    for result in results:
        path = result['path'].lower() # Path of the resulted endpoints
        http_method = result['method'].lower() # Method of the resulted endpoints
        # if (http_method == method) and (path.startswith(f"/api/{target_entity}")):
        if (http_method == method) and (f"/{target_entity}" in path):
            relevant_apis.append(result)

    relevant_apis.sort(key=lambda x: x['score']) # lower distance = more relevant
    return relevant_apis[:max_results]


@mcp.tool()
async def retrieve_api_endpoint(query: str, method:str, target_entity:str) -> dict:
    """
    MCP tool that finds the most relevant API endpoint for a given query.

    NOTE:
    - Use short, action-based phrases (not full sentences).
    - Avoid long descriptive text.

    Recognized Entities:
    The following are the main entities in the API schema. Use them as targets when interpreting the query. 
    Try to leave s at the end as some are plural and some singular if you keep s at the end then you might miss some:
    - customers
    - projects
    - users
    - marketplace
    - marketplace-orders
    - marketplace-resource
    - marketplace-plans
    - marketplace-service-providers
    - marketplace-provider-offerings
    - marketplace-offering-permissions
    - user-invitations
    - roles
    - support
    - billing


    Example queries (use these styles):
    - "add user to project"
    - "create marketplace-offering"
    - "delete customer"
    - "list support requests"
    - "update user roles"
    - "terminate marketplace-resources"

    Avoid full sentences like:
    - "get all users with detailed information"
    - "I want to register a new service provider"

    Args:
        query (str): Short, keyword-rich phrase (e.g., "add user to project").
        method (str): HTTP method ("GET", "POST", "PATCH", "DELETE").
        target_entity (str): Entity like "customers", "projects", etc.

    Returns:
        dict : Contains the query, a list of results, and an optional message.
    """
    init_cache_dir()
    # Step 1: Retrieve candidates (embedding + FAISS)
    results = await retrieve_relevant_apis(query=query, k=20)
    # Step 2: Filter by method + entity
    final_apis = post_filter_results(results, method, target_entity)
    if not final_apis:
        return {
            "query": query,
            "results": [],
            "message": f"No relevant API endpoint found for: '{query}'. Try simplifying the query."
        }
    # Step 3: Return candidate list
    return {
        "query": query,
        "results": [
            {
                "path": api["path"],
                "method": api["method"],
                "description": api.get("description", ""),
                "score": float(api.get("score", 0.0)),  # you can propagate FAISS score if stored
            }
            for api in final_apis
        ]
    }