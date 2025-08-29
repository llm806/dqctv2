import os

IGNORE_DIRS = {"node_modules", ".venv", "__pycache__", "dist", "build"}

def print_tree(startpath, prefix=""):
    items = sorted(os.listdir(startpath))
    for index, item in enumerate(items):
        path = os.path.join(startpath, item)
        connector = "└── " if index == len(items) - 1 else "├── "
        if os.path.isdir(path):
            if item in IGNORE_DIRS:
                continue
            print(prefix + connector + f"[{item}]")
            new_prefix = prefix + ("    " if index == len(items) - 1 else "│   ")
            print_tree(path, new_prefix)
        else:
            print(prefix + connector + item)

if __name__ == "__main__":
    print_tree(".")
