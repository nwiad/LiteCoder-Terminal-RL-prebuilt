# Makefile for legacy project (outdated, references wrong paths)

CC = /usr/local/legacy/bin/gcc
CXX = /usr/local/legacy/bin/g++
CFLAGS = -Wall -Werror -I/home/developer/libs/custom/include -Iinclude
CXXFLAGS = -Wall -Werror -std=c++0x -I/home/developer/libs/custom/include -Iinclude
LDFLAGS = -L/home/developer/libs/custom/lib -lutillib -lm

SRCDIR = src
OBJDIR = obj
BINDIR = bin

MATH_SRCS = $(SRCDIR)/mathtools_main.cpp $(SRCDIR)/math_utils.c $(SRCDIR)/math_advanced.cpp
TEXT_SRCS = $(SRCDIR)/textproc_main.cpp $(SRCDIR)/text_utils.cpp $(SRCDIR)/string_helpers.c

all: mathtools textproc

mathtools: $(MATH_SRCS)
	$(CXX) $(CXXFLAGS) -o $(BINDIR)/mathtools $(MATH_SRCS) $(LDFLAGS)

textproc: $(TEXT_SRCS)
	$(CXX) $(CXXFLAGS) -o $(BINDIR)/textproc $(TEXT_SRCS) $(LDFLAGS)

clean:
	rm -f $(BINDIR)/*
	rm -f $(OBJDIR)/*

.PHONY: all clean
