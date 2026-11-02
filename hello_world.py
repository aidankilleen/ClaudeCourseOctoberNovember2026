import sys

def greet(name):
    return f"Hello, {name}! Welcome to Python."

print("Python is working!")
print("Version:", sys.version.split()[0])

name = input("What's your name? ")
print(greet(name))

total = 0
for n in range(1, 6):
    total += n
print("Sum of 1 to 5 is", total)