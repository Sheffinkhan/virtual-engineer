from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from io import BytesIO
from openai import OpenAI
from dotenv import load_dotenv
import os
import re
import time

app = Flask(__name__)
CORS(app)

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables.")

client = OpenAI(api_key=api_key)

SUPPORTED_EXTENSIONS = {'.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.pdf', '.docx', '.csv', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp'}
# file path
directory_path = "project"  

def create_file(client, file_path):
    with open(file_path, "rb") as file_content:
        file_name = os.path.basename(file_path)
        file_tuple = (file_name, file_content)
        result = client.files.create(file=file_tuple, purpose="assistants")
    return result.id

file_ids = []
for filename in os.listdir(directory_path):
    file_path = os.path.join(directory_path, filename)
    if os.path.isfile(file_path):
        _, ext = os.path.splitext(filename)
        if ext.lower() in SUPPORTED_EXTENSIONS:
            file_id = create_file(client, file_path)
            file_ids.append(file_id)

vector_store = client.vector_stores.create(name="knowledge_base")
for file_id in file_ids:
    client.vector_stores.files.create(vector_store_id=vector_store.id, file_id=file_id)

assistant = client.beta.assistants.create(
    name="File Explainer",
    instructions="You are an assistant that explains the contents of files in a vector store and suggests code changes when asked.",
    model="gpt-3.5-turbo",
    tools=[{"type": "file_search"}],
    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
)

@app.route('/api/process', methods=['POST'])
def process_prompt():
    data = request.get_json()
    prompt = data.get('prompt', '')
    print(f"Received prompt: {prompt}")

    thread = client.beta.threads.create()
    message = client.beta.threads.messages.create(thread_id=thread.id, role="user", content=prompt)
    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)

    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run_status.status == "completed":
            break
        time.sleep(1)

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    response = messages.data[0].content[0].text.value
    print(f"Response: {response}")

    file_name_pattern = r"`([^`]+?\.(?:css|html|js|py|txt))`"
    code_block_pattern = r"```(?:css|python|html|js)?\n(.*?)```"
    file_name_matches = re.findall(file_name_pattern, response)
    code_block_match = re.search(code_block_pattern, response, re.DOTALL)

    result = {"response": response}
    if not file_name_matches or not code_block_match:
        result["status"] = "Error: Could not extract file name or code block."
    else:
        file_name = file_name_matches[0]
        new_code = code_block_match.group(1).strip()
        target_file_path = os.path.join(directory_path, file_name)

        def update_css_content(existing_content, new_code):
            properties = [prop.strip() for prop in new_code.split(';') if prop.strip()]
            updated_content = existing_content
            for prop in properties:
                prop_match = re.match(r"([^:]+)\s*:\s*(.+)", prop)
                if prop_match:
                    prop_name, prop_value = prop_match.groups()
                    prop_name = prop_name.strip()
                    pattern = rf"{prop_name}\s*:\s*[^;]+;"
                    if re.search(pattern, updated_content):
                        updated_content = re.sub(pattern, f"{prop_name}: {prop_value};", updated_content)
                    else:
                        updated_content = updated_content.rstrip() + f"\n{prop_name}: {prop_value};\n"
            return updated_content

        if os.path.exists(target_file_path):
            with open(target_file_path, "r") as f:
                existing_content = f.read()
            if file_name.endswith('.css') or '{' in new_code:
                updated_content = update_css_content(existing_content, new_code)
                if updated_content != existing_content:
                    with open(target_file_path, "w") as f:
                        f.write(updated_content)
                    result["status"] = f"Updated {file_name} with new changes."
                else:
                    result["status"] = f"No changes needed in {file_name}; content already up to date."
            else:
                if new_code not in existing_content:
                    with open(target_file_path, "a") as f:
                        f.write("\n" + new_code + "\n")
                    result["status"] = f"Appended new code to {file_name}."
                else:
                    result["status"] = f"No changes made to {file_name}; the suggested code is already present."
        else:
            with open(target_file_path, "w") as f:
                f.write(new_code + "\n")
            result["status"] = f"Created {file_name} as it didn't exist previously."

    return jsonify(result)

# Serve static files from the directory
@app.route('/files/<path:filename>')
def serve_files(filename):
    return send_from_directory(directory_path, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
