import os
import ast
import sys
import stdlib_list

# 현재 파이썬 버전 기준 표준 라이브러리 목록
std_libs = set(stdlib_list.stdlib_list(f"{sys.version_info.major}.{sys.version_info.minor}"))

external_modules = set()

def is_external(name):
    return name.split('.')[0] not in std_libs

def find_imports_in_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            return
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if is_external(alias.name):
                    external_modules.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and is_external(node.module):
                external_modules.add(node.module.split('.')[0])

def scan_project(root_dir):
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".py"):
                find_imports_in_file(os.path.join(dirpath, filename))

if __name__ == "__main__":
    scan_project(".")  # 현재 폴더 기준
    print("🔍 외부 모듈 목록:")
    for module in sorted(external_modules):
        print(f"- {module}")