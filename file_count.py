import requests
import json
from collections import defaultdict

GITHUB_API_URL = "https://api.github.com"
REPO_OWNER = "totally-not-frito-lays"  # Replace with the repo owner (can be a user or org)
REPO_NAME = "swapy-sandbox"  # Replace with the repo name

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

def fetch_files(repo_owner, repo_name):
    url = f"{GITHUB_API_URL}/repos/{repo_owner}/{repo_name}/git/trees/main?recursive=1"
    response = requests.get(url)
    if response.status_code == 403:
        print("Rate limit exceeded. Try again later.")
        exit()
    return response.json()['tree']

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
    response = requests.get(url)
    if response.status_code == 403:
        print("Rate limit exceeded. Try again later.")
        exit()
    return response.json()

def write_results_to_file(data, filename):
    with open(filename, "w") as file:
        file.write(json.dumps(data, indent=4))

def count_lines_per_file(repo_owner, repo_name):
    url = f"{GITHUB_API_URL}/repos/{repo_owner}/{repo_name}/git/trees/main?recursive=1"
    response = requests.get(url)
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
            file_response = requests.get(file_url)
            if file_response.status_code == 403:
                print("Rate limit exceeded. Try again later.")
                exit()
            file_content = file_response.json()['content']
            line_counts[file_path] = file_content.count('\n')
    
    return line_counts

def main():
    files = fetch_files(REPO_OWNER, REPO_NAME)
    language_counts = count_files(files, FILE_EXTENSIONS)
    languages_data = fetch_language_bytes(REPO_OWNER, REPO_NAME)

    print("File count per language:")
    for language, count in language_counts.items():
        print(f"{language}: {count} files")

    print("\nLanguages used (by bytes):")
    for language, bytes in languages_data.items():
        print(f"{language}: {bytes} bytes")

    line_counts = count_lines_per_file(REPO_OWNER, REPO_NAME)
    
    print("\nLine count per file:")
    for file_path, line_count in line_counts.items():
        print(f"{file_path}: {line_count} lines")

    write_results_to_file(languages_data, "language_statistics.json")

if __name__ == "__main__":
    main()
