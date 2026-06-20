#include <iostream>
#include <string>

class Student {
public:
    std::string name;
    int age;
};

int main() {
    Student student{"Ayesha", 20};
    if (student.age >= 18) {
        std::cout << student.name << std::endl;
    }
    return 0;
}

