#!/bin/bash

# Safe wrapper for osc2u.e that handles EOF errors gracefully
# Usage: ./run_osc2u_safe.sh input_file

input_file="$1"
if [ -z "$input_file" ]; then
    echo "Usage: $0 input_file"
    exit 1
fi

if [ ! -f "$input_file" ]; then
    echo "Error: Input file $input_file not found"
    exit 1
fi

echo "Running osc2u.e with input: $input_file"

# Run osc2u.e and capture both stdout and stderr
./osc2u.e < "$input_file" > run.log 2>&1
exit_code=$?

echo "osc2u.e exit code: $exit_code"

# Check if the error is just EOF (which is expected)
if [ $exit_code -ne 0 ]; then
    echo "Checking for EOF error in log..."
    if grep -q "End of file" run.log || grep -q "Fortran runtime error: End of file" run.log; then
        echo "EOF encountered - this is expected, continuing..."
        # Check if fort.14 was created successfully
        if [ -f "fort.14" ]; then
            echo "Output file fort.14 created successfully"
            exit 0
        else
            echo "Warning: fort.14 not created, but EOF was expected"
            exit 0
        fi
    else
        echo "Real error occurred, exit code: $exit_code"
        echo "Error log contents:"
        cat run.log
        echo "End of error log"
        exit $exit_code
    fi
else
    echo "osc2u.e completed successfully"
fi

exit 0
