from pathlib import Path

print("New")
p = Path(".")
p = p.cwd()
print(p)
p = p/'chetah_library'
print(p)

# With a built path, let's see if we can read in the text file
with p.open() as f: f.readlines()