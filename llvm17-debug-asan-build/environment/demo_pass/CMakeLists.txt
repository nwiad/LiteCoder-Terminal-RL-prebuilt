cmake_minimum_required(VERSION 3.20)
project(DemoPrintPass)

find_package(LLVM REQUIRED CONFIG)

message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")
message(STATUS "Using LLVMConfig.cmake in: ${LLVM_DIR}")

include_directories(${LLVM_INCLUDE_DIRS})
separate_arguments(LLVM_DEFINITIONS_LIST NATIVE_COMMAND ${LLVM_DEFINITIONS})
add_definitions(${LLVM_DEFINITIONS_LIST})

add_library(DemoPrintPass MODULE DemoPrintPass.cpp)

target_compile_features(DemoPrintPass PRIVATE cxx_std_17)

# No need to link against LLVM libs for a pass plugin loaded into clang/opt
set_target_properties(DemoPrintPass PROPERTIES
    PREFIX ""
    SUFFIX ".so"
)

if(NOT LLVM_ENABLE_RTTI)
    target_compile_options(DemoPrintPass PRIVATE -fno-rtti)
endif()
