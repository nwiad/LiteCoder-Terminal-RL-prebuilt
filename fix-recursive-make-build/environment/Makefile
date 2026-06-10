# Broken top-level Makefile - no variable exports, no dependencies
SUBDIRS = libcore libutils app

all:
	for dir in $(SUBDIRS); do \
		$(MAKE) -C $$dir; \
	done

clean:
	for dir in $(SUBDIRS); do \
		$(MAKE) -C $$dir clean; \
	done
	rm -rf lib bin

.PHONY: all clean
