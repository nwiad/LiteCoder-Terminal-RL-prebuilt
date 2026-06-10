# CMakeLists.txt for utility library
# BUG: references wrong variable and missing include path

add_library(utillib STATIC
    util_lib.c
)

# BUG: hardcoded path that doesn't exist
target_include_directories(utillib PUBLIC /home/developer/libs/custom/include)
target_include_directories(utillib PUBLIC ${PROJECT_SOURCE_DIR}/headers)
