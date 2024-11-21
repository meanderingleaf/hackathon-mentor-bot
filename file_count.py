import requests
from collections import defaultdict

GITHUB_API_URL = "https://api.github.com"
REPO_OWNER = "totally-not-frito-lays"  # Replace with the repo owner (can be a user or org)
REPO_NAME = "23-Workshop-Recursion-Turtles_Trees"  # Replace with the repo name

# Define file extensions for different languages
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

# Fetch the list of files in the repository (recursively)
url = f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/main?recursive=1"
response = requests.get(url)

# Handle rate limits and errors
if response.status_code == 403:
    print("Rate limit exceeded. Try again later.")
    exit()

files_data = response.json()
files = files_data['tree']

# Dictionary to store file counts per language
language_counts = defaultdict(int)

# Count files per language
for file in files:
    if file['type'] == 'blob':  # Only count actual files
        file_path = file['path']
        for language, extensions in FILE_EXTENSIONS.items():
            if any(file_path.endswith(ext) for ext in extensions):
                language_counts[language] += 1
                break

# Fetch language byte count from GitHub API
languages_url = f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/languages"
languages_response = requests.get(languages_url)

# Handle rate limits and errors
if languages_response.status_code == 403:
    print("Rate limit exceeded. Try again later.")
    exit()

languages_data = languages_response.json()

# Combine the file count and byte count data
print("File count per language:")
for language, count in language_counts.items():
    print(f"{language}: {count} files")

print("\nLanguages used (by bytes):")
for language, bytes in languages_data.items():
    print(f"{language}: {bytes} bytes")
