public class Student {
    private String name = "Ayesha";
    private int age = 20;

    public boolean isAdult() {
        return age >= 18;
    }

    public static void main(String[] args) {
        Student student = new Student();
        System.out.println(student.name);
    }
}

