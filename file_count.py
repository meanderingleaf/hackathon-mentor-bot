import json
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import requests
from collections import defaultdict
from dotenv import load_dotenv
import os

GITHUB_API_URL = "https://api.github.com"
load_dotenv()
GITHUB_PAT = os.getenv("GITHUB_PAT")


#set up the variables here for the inital mongo DB needs to be in the envfile  DONE
load_dotenv()
uri = os.environ('mongo_uri')
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
#ping server 
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

FILE_EXTENSIONS = {
    'Python': ['.py'],
    'JavaScript': ['.js'],
    'Java': ['.java'],
    'C++': ['.cpp', '.h'],
    'Ruby': ['.rb'],
    'Go': ['.go'],
    'HTML': ['.html', '.htm'],
    'CSS': ['.css'],
    'Markdown': ['.md'],
    'Text': ['.txt', '.log'],
}

def get_headers():
    headers = {}
    if GITHUB_PAT:
        headers["Authorization"] = f"token {GITHUB_PAT}"
    return headers

def fetch_files(repo_owner, repo_name):
    response = requests.get(f"{GITHUB_API_URL}/repos/{repo_owner}/{repo_name}/git/trees/main?recursive=1", headers=get_headers())
    response_data = response.json()
    # print(f"{response_data = }")
    
    if 'tree' in response_data:
        return response_data['tree']
    else:
        print(f"Error: 'tree' key not found in the response for repo {repo_owner}/{repo_name}")
        return []

def count_files(files, file_extensions):
    language_counts = defaultdict(int)
    for file in files:
        if file['type'] == 'blob':
            file_path = file['path']
            for language, extensions in file_extensions.items():
                if any(file_path.endswith(ext) for ext in extensions):
                    language_counts[language] += 1
                    break
    return language_counts

def fetch_language_bytes(repo_owner, repo_name):
    url = f"{GITHUB_API_URL}/repos/{repo_owner}/{repo_name}/languages"
    response = requests.get(url, headers=get_headers())
    if response.status_code == 403:
        print("Rate limit exceeded. Try again later.")
        exit()
    return response.json()

def count_lines_per_file(repo_owner, repo_name):
    url = f"{GITHUB_API_URL}/repos/{repo_owner}/{repo_name}/git/trees/main?recursive=1"
    response = requests.get(url, headers=get_headers())
    if response.status_code == 403:
        print("Rate limit exceeded. Try again later.")
        exit()
    files = response.json()['tree']
    
    ignored_extensions = ['.json', '.md', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.pdf', '.zip', '.tar', '.gz', '.rar', '.7z', '.exe', '.dll', '.so', '.dylib', '.gitignore', '.yaml', '.yml']
    ignored_directories = ['node_modules', 'venv', 'lib', 'libs', 'dist', 'build']
    
    line_counts = {}
    for file in files:
        if file['type'] == 'blob':
            file_path = file['path']
            if '.' not in file_path or any(file_path.endswith(ext) for ext in ignored_extensions) or any(dir in file_path.split('/') for dir in ignored_directories):
                continue
            file_url = f"{GITHUB_API_URL}/repos/{repo_owner}/{repo_name}/git/blobs/{file['sha']}"
            file_response = requests.get(file_url, headers=get_headers())
            if file_response.status_code == 403:
                print("Rate limit exceeded. Try again later.")
                exit()
            file_content = file_response.json()['content']
            line_counts[file_path] = file_content.count('\n')
    
    return line_counts

def process_repo(repo_owner, repo_name):
    files = fetch_files(repo_owner, repo_name)
    language_counts = count_files(files, FILE_EXTENSIONS)
    languages_data = fetch_language_bytes(repo_owner, repo_name)
    line_counts = count_lines_per_file(repo_owner, repo_name)

    total_lines = sum(line_counts.values())
    total_files = len(line_counts)
    total_size = sum(languages_data.values())

    repo_stats = {
        "total_lines": total_lines,
        "total_files": total_files,
        "total_size": total_size
    }

    repo_breakdown = {}
    for language, count in language_counts.items():
        repo_breakdown[language.lower()] = {
            "name": language,
            "count": count,
            "lines": sum(line_counts[file] for file in line_counts if file.endswith(tuple(FILE_EXTENSIONS[language]))),
            "size": languages_data.get(language, 0)
        }

    return {
        "discord_user": "user",
        "github_user": repo_owner,
        "github_repo": repo_name,
        "file_stats": {
            "repo_stats": repo_stats,
            "repo_breakdown": repo_breakdown
        }
    }



#   Not sure if this is the way to go, without being able to test bot can't tell.
#  def write_results_to_mongo(data):
#     db = client['hackathon']
#     collection = db['github_stats']
#     collection.insert_one(data)

def insert_data_to_mongo(data):
   # with open('global_stats.json') as f:
       # data = json.load(f)
    db = client['hackathon']
    collection = db['global_stats']  #sure naming syntax can be changed
    #or many 
    collection.insert_many(data)

#Need to test
#Function for Repos 
def add_repo_to_db(owner, repo_name, added_by, client):
    db = client['hackathon']
    collection = db['global_stats']
    doc = collection.find_one()

    if not doc:
        return False  # No global_stats document exists

    # Check if repo already exists in repo_array
    for repo in doc.get("repo_array", []):
        if repo["github_user"] == owner and repo["github_repo"] == repo_name:
            return False  # Duplicate found

    # Process the repo to attach file_stats
    from file_count import process_repo  # import here to avoid circular import
    try:
        repo_data = process_repo(owner, repo_name)
        repo_data["discord_user"] = added_by
    except Exception as e:
        print(f"Failed to process repo: {e}")
        return False

    # Push the new repo into the repo_array
    collection.update_one(
        {"_id": doc["_id"]},
        {"$push": {"repo_array": repo_data}}
    )

    return True


    
def get_all_repos_from_global_stats(client):
    db = client['hackathon']
    collection = db['global_stats']
    doc = collection.find_one()

    if not doc or "repo_array" not in doc:
        return []

    return doc["repo_array"]


#stays the same? 
#def write_results_to_file(data, filename):
   # with open(filename, 'w') as f:
     #   json.dump(data, f, indent=4)

    

def main():
    # Get all GitHub repos added via the bot
    repos = get_all_repos_from_global_stats(client)

    if not repos:
        print("No repositories found in the database.")
        return

    global_stats = {
        "total_lines": 0,
        "total_files": 0,
        "total_size": 0,
        "languages": set()
    }

    repo_array = []

    for repo in repos:
        repo_data = process_repo(repo["github_user"], repo["github_repo"])
        repo_array.append(repo_data)

        global_stats["total_lines"] += repo_data["file_stats"]["repo_stats"]["total_lines"]
        global_stats["total_files"] += repo_data["file_stats"]["repo_stats"]["total_files"]
        global_stats["total_size"] += repo_data["file_stats"]["repo_stats"]["total_size"]
        global_stats["languages"].update(repo_data["file_stats"]["repo_breakdown"].keys())

    global_stats["languages"] = list(global_stats["languages"])

    output_data = {
        "global-stats": global_stats,
        "repo_array": repo_array
    }

    # Write directly to MongoDB
    insert_data_to_mongo(output_data)

    print("Stats successfully inserted into MongoDB.")
