# Legacy Makefile for libmini
# This is the old build system that needs to be replaced with autotools

CC = gcc
CFLAGS = -Wall -O2 -fPIC
AR = ar
ARFLAGS = rcs

SOURCES = mini.c
OBJECTS = $(SOURCES:.c=.o)
LIBRARY = libmini.a
SHARED_LIB = libmini.so

all: $(LIBRARY) $(SHARED_LIB)

$(LIBRARY): $(OBJECTS)
	$(AR) $(ARFLAGS) $@ $^

$(SHARED_LIB): $(OBJECTS)
	$(CC) -shared -o $@ $^

%.o: %.c mini.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJECTS) $(LIBRARY) $(SHARED_LIB)

.PHONY: all clean
