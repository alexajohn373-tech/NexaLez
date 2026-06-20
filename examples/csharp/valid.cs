using System;

public class Student
{
    public string Name { get; set; } = "Ayesha";
    public int Age { get; set; } = 20;

    public bool IsAdult()
    {
        return Age >= 18;
    }

    public static void Main()
    {
        var student = new Student();
        Console.WriteLine(student.Name);
    }
}

