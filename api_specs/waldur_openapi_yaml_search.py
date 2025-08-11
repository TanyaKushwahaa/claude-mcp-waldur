import yaml
import os
import requests

# cache_dir = "./cache_dir"
# def load_api_schema(url="https://docs.waldur.com/latest/API/waldur-openapi-schema.yaml") -> Dict:
#     """ Load the OpenAPI schema from the given URL. """

#     cache_file = f"{cache_dir}/waldur-openapi-schema.yaml"
    
#     # Load from cache if available
#     if os.path.exists(cache_file):
#         with open(cache_file, 'r') as f:
#             try:
#                 api_schema = yaml.safe_load(f)
#                 # print("Loaded the OpenAPI schema from cache")
#             except Exception as e:
#                 print(f"Error loading cached schema: {e}")

#     # if cache is not available, download and cache it
#     else:
#         # print(f"Downloading OpenAPI schema from URL {url}...")
#         response = requests.get(url)
#         api_schema = yaml.safe_load(response.text)

#         # Cache the schema
#         with open(cache_file, 'w') as f:  
#             yaml.dump(api_schema, f)
#             # print(f"API schema cached to {cache_file}")

#     chunks = process_api_schema(api_schema)
#     return chunks

url="https://docs.waldur.com/latest/API/waldur-openapi-schema.yaml"
response = requests.get(url)
# print(response.text)
data = yaml.safe_load(response.text)
# print(data.items())
path_list = []

get_apis = []
post_apis = []
patch_apis = []
delete_apis = []

if "paths" in data:
    for paths, methods in data['paths'].items():
        for method in methods:
            # print(paths, method)
            if method == "get":
                get_apis.append(paths)
            elif method == "patch":
                patch_apis.append(paths)
            elif method == "post":
                post_apis.append(paths)
            elif method == "delete":
                delete_apis.append(paths)

stripped_get = set()
for get_api in get_apis:
    path_parts = get_api.lstrip("/").rstrip("/").split("/")
    stripped_get.add(tuple(path_parts[:2]))
print(len(stripped_get))

# print(stripped_get)


print(len(get_apis), len(patch_apis), len(post_apis), len(delete_apis))


#     # for paths, methods in v.items():
#         print(paths, methods)
#         path_list.append(paths)
# print(len(path_list))