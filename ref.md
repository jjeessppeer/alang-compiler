## Variable declaration
# Variables must be declared before used. No value is assigned on declaration.
# Variables are available in the current function block and below.
```
var a;      # Allocate single memory row
var a[10];  # Allocate memory range
```

## Variable assignment
a, b, and c can be any declared variable or a constant number.
```
a = 1;          # Copy constant '1'.
a = *1;         # Copy value from address '1'.
a = b;          # Copy value from 'b'.
a = &b;         # Copy address of 'b'.
a = *b;         # Copy value from address pointed to by 'b'. Ex if b=100, then copy the value from address row 100 into a.
a = func_x();   # Copy the value returned from the function.

*1 = x;         # Copy to address '1'
*a = x;         # Copy to address 'a'

## Expressions
# Expressions are always resolved left to right. Order of operations is not respected. 1+2*3 will resolve 1+2 first.
a = b + c;
a = b - c;
a = b * c;
a = b << c;
``` 

## Function declaration
```
// Basic function declaration
function func_simple() {
}

// Functions can return a single value.
function func_return() {
    return 10;
}

// Function parameters
function func_params(x,y) {
    x = y + 50;
    return x;
}
```

## Control statements
```
return;     // Return from function.
return x;   // Return from function with value.
halt;       // Stop code execution.
```

## Conditional
```
// Conditional branching
if (a<b) {
    // code...
}
if (a>b) {}
if (a!=b) {}
if (a==b) {}

// Conditional looping
while (a<b) {}
```