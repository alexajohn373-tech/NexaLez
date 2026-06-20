#include <stdio.h>

int main(void) {
    int age = 20;
    float score = 91.5;
    char grade = 'A';

    if (age >= 18 && score > 80) {
        printf("Eligible: %c\n", grade);
    }
    return 0;
}

