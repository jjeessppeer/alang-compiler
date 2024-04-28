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
a = b;          # Copy value from 'b'.
a = &b;         # Copy address of 'b'.
a = *b;         # Copy value from address pointed to by 'b'. Ex if b=100, then copy the value from address row 100 into a.
a = b[c];       # Copy value from the address x rows after 'b'. Ex if b is stored on row 5 copy the value of row 5+c into a.
a = func_x();   # Copy the value returned from the function.

*a = b          # Copy value from 'b' to address pointed to by 'a'.

## Expressions
# Expressions are always resolved left to right. Order of operations is not respected. 1+2*3 will resolve 1+2 first.
a = b + c;
a = b - c;
a = b * c;
a = b << c;
``` 

## Special statements
```
return;     // Return from function.
return x;   // Return from function with value.
halt;       // Stop code execution.
```

## Function declaration
```
function func_name(param_1,param_2) {
}
```

## Conditional
```
if a < b {   
}
if a > b {   
}
if a != b {   
}
```