import json
import requests
from collections import defaultdict
from dotenv import load_dotenv
import os

GITHUB_API_URL = "https://api.github.com"
load_dotenv()
GITHUB_PAT = os.getenv("GITHUB_PAT")

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

def write_results_to_file(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

def main():
    repos = [
        {"owner": "totally-not-frito-lays", "name": "swapy-sandbox"},
        {"owner": "meanderingleaf", "name": "hackathon-mentor-bot"},
        # Add more repositories as needed
    ]

    global_stats = {
        "total_lines": 0,
        "total_files": 0,
        "total_size": 0,
        "languages": set()
    }

    repo_array = []

    for repo in repos:
        repo_data = process_repo(repo["owner"], repo["name"])
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

    write_results_to_file(output_data, "global_stats.json")

if __name__ == "__main__":
    main()
