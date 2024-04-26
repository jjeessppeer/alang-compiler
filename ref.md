## Variable declaration
# Variables must be declared before used. No value is assigned on declaration.
# Variables are available in the current function block and below.
```
var a;      # Allocate single memory row variable 
var a[10];  # Allocate memory range
```

## Variable assignment
a, b, and c can be any declared variable or number.
```
a = b;          # Copy value from 'b'.
a = &b;         # Copy address of 'b'.
a = *b;         # Copy value from address pointed to by 'b'. Ex if b=100, then copy the value from address row 100 into a.
a = b[c];       # Copy value from the address x rows after 'b'. Ex if b is stored on row 5 copy the value of row 5+x into a.
a = func();     # Copy the value returned from the function.

# Math assignment
a = b + c;
a = b - c;
a = b * c;
a = b <<;
``` 


## Function declaration
```
function func_name() {
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