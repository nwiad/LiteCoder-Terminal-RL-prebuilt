# Broken app Makefile - missing include path and wrong library order
CC = gcc
CFLAGS = -Wall -O2
LDFLAGS = -L../lib

BINDIR = ../bin
TARGET = $(BINDIR)/app

SRCS = main.c
OBJS = $(SRCS:.c=.o)

# Wrong library order - libutils before libcore
LIBS = -lutils -lcore

all: $(TARGET)

$(TARGET): $(OBJS)
	mkdir -p $(BINDIR)
	$(CC) $(OBJS) $(LDFLAGS) $(LIBS) -o $@

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)

.PHONY: all clean
