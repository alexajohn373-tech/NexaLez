"""Valid Python sample."""

class Student:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    def is_adult(self):
        return self.age >= 18


students = [Student("Ayesha", 20), Student("Ali", 16)]
for student in students:
    if student.is_adult():
        print(f"{student.name} is eligible")

