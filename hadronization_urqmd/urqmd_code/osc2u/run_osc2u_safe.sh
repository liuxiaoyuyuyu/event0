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
echo "=== osc2u.e output (live) ==="

# Run osc2u.e and show output in real-time, but also capture to log
# This will show both normal output and errors on screen, and save both to run.log
./osc2u.e < "$input_file" 2>&1 | tee run.log
exit_code=${PIPESTATUS[0]}

echo "=== End of osc2u.e output ==="
echo "osc2u.e exit code: $exit_code"

# Check if the error is just EOF (which is expected)
if [ $exit_code -ne 0 ]; then
    echo "Checking for EOF error in log..."
    if grep -q "End of file" run.log || grep -q "Fortran runtime error: End of file" run.log; then
        echo "EOF encountered - this is expected, continuing..."
    else
        echo "Real error occurred, exit code: $exit_code"
        exit $exit_code
    fi
fi

# Always check if fort.14 was created successfully
if [ -f "fort.14" ]; then
    echo "Output file fort.14 created successfully"
    exit 0
else
    echo "Warning: fort.14 not created"
    exit 1
fi

exit 0
