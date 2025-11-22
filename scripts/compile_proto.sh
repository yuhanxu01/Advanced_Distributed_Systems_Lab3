#!/bin/bash
# Compile Protocol Buffers

cd "$(dirname "$0")/.."

python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./proto \
    --grpc_python_out=./proto \
    ./proto/two_phase_commit.proto

# Fix imports in generated files
sed -i 's/import two_phase_commit_pb2/from . import two_phase_commit_pb2/' proto/two_phase_commit_pb2_grpc.py 2>/dev/null || \
sed -i '' 's/import two_phase_commit_pb2/from . import two_phase_commit_pb2/' proto/two_phase_commit_pb2_grpc.py

echo "Protocol buffers compiled successfully!"
