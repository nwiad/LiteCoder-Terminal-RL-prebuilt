# Broken libcore Makefile - missing include path
CC = gcc
CFLAGS = -Wall -O2
AR = ar
ARFLAGS = rcs

LIBDIR = ../lib
TARGET = $(LIBDIR)/libcore.a

SRCS = core.c
OBJS = $(SRCS:.c=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	mkdir -p $(LIBDIR)
	$(AR) $(ARFLAGS) $@ $^

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)

.PHONY: all clean
