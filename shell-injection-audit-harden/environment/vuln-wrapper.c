#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
 * reader — SUID-root helper that lets unprivileged users
 *          read files inside /srv/secure/.
 *
 * Usage:  /opt/reader <filename>
 *
 * The program prepends the base directory and uses system()
 * to invoke cat on the resulting path.
 */

#define BASE_DIR "/srv/secure/"

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <filename>\n", argv[0]);
        return 1;
    }

    char cmd[512];
    sprintf(cmd, "cat %s%s", BASE_DIR, argv[1]);
    system(cmd);

    return 0;
}
