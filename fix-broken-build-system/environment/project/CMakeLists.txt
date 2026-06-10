# CMakeLists.txt for legacy project
# Last updated: 2014-03-15

cmake_minimum_required(VERSION 2.6)

project(LegacyTools)

# Hardcoded path that doesn't exist
set(CMAKE_INSTALL_PREFIX "/opt/legacy_tools/v2.3")
set(CUSTOM_LIB_PATH "/home/developer/libs/custom")

# Wrong C++ standard syntax
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Werror")

# Include directories - one path is wrong
include_directories(${PROJECT_SOURCE_DIR}/include)
include_directories(${CUSTOM_LIB_PATH}/include)
include_directories(${PROJECT_SOURCE_DIR}/headers)

# Add the utility library from wrong path
add_subdirectory(${PROJECT_SOURCE_DIR}/lib)

# Source files for mathtools - references nonexistent file
add_executable(mathtools
    src/mathtools_main.cpp
    src/math_utils.c
    src/math_advanced.cpp
)

# Source files for textproc - references nonexistent file
add_executable(textproc
    src/textproc_main.cpp
    src/text_utils.cpp
    src/string_helpers.c
)

# Link against the utility library
target_link_libraries(mathtools utillib m)
target_link_libraries(textproc utillib)

# Broken install targets
install(TARGETS mathtools textproc DESTINATION ${CUSTOM_LIB_PATH}/bin)
