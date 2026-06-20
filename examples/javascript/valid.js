class Student {
    constructor(name, age) {
        this.name = name;
        this.age = age;
    }

    isAdult() {
        return this.age >= 18;
    }
}

const student = new Student("Ayesha", 20);
if (student.isAdult()) {
    console.log(`${student.name} is eligible`);
}

