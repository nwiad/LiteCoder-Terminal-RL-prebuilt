#!/usr/bin/env python3
"""
Setup script for broken autotools cross-compilation project.
Creates a misconfigured build system that requires fixing.
"""

import os
import shutil
import stat

def create_directory_structure():
    """Create the project directory structure."""
    directories = ["src"]
    for directory in directories:
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory, exist_ok=True)
    print(f"Created directory structure: {directories}")

def create_hello_c():
    """Create the Hello World C source file."""
    hello_c_content = """#include <stdio.h>

int main() {
    printf("Hello, World!\\n");
    return 0;
}
"""
    with open("src/hello.c", "w") as f:
        f.write(hello_c_content)
    print("Created src/hello.c")

def create_configure_ac():
    """Create a broken configure.ac file with cross-compilation issues."""
    configure_ac_content = """dnl Process this file with autoconf to produce a configure script.
AC_PREREQ([2.69])
AC_INIT([hello], [1.0], [bug-report@example.com])
AC_CONFIG_SRCDIR([src/hello.c])
AC_CONFIG_HEADERS([config.h])
AC_PROG_CC

AC_ARG_ENABLE([cross-compile],
    [AS_HELP_STRING([--enable-cross-compile],
        [Enable cross-compilation mode (experimental)])])

AC_ARG_WITH([target],
    [AS_HELP_STRING([--with-target], [Specify target architecture])],
    [target=$withval],
    [target=unknown])

AC_MSG_CHECKING([for target environment])
AC_MSG_RESULT([$target])

AC_CHECK_PROG([PERL], [perl], [perl], [no])

AC_CHECK_TOOL([AS], [as], [no])

AC_CONFIG_FILES([Makefile])
AC_OUTPUT
"""
    with open("configure.ac", "w") as f:
        f.write(configure_ac_content)
    print("Created configure.ac with missing cross-compilation macros")

def create_makefile_am():
    """Create a broken Makefile.am with build configuration issues."""
    makefile_am_content = """# Automake input for hello package.

bin_PROGRAMS = hello
hello_SOURCES = src/hello.c

INCLUDES = -I/usr/include
"""
    with open("Makefile.am", "w") as f:
        f.write(makefile_am_content)
    print("Created Makefile.am with build issues")

def create_missing_config_files():
    """Create placeholder/missing config files - this is the broken state."""
    config_guess_content = """#!/bin/sh
target="x86_64-unknown-linux-gnu"
exit 0
"""
    with open("config.guess", "w") as f:
        f.write(config_guess_content)
    os.chmod("config.guess", os.stat("config.guess").st_mode | stat.S_IXUSR)
    print("Created broken config.guess that does not detect ARM")

    config_sub_content = """#!/bin/sh
case "$1" in
    *)
        echo "unknown"
        exit 0
        ;;
esac
"""
    with open("config.sub", "w") as f:
        f.write(config_sub_content)
    os.chmod("config.sub", os.stat("config.sub").st_mode | stat.S_IXUSR)
    print("Created incomplete config.sub")

def main():
    """Main setup function - creates the broken project structure."""
    print("Setting up broken autotools cross-compilation project...")
    print()

    create_directory_structure()
    create_hello_c()
    create_configure_ac()
    create_makefile_am()
    create_missing_config_files()

    print()
    print("Setup complete. The project is ready for cross-compilation debugging.")

if __name__ == "__main__":
    main()
