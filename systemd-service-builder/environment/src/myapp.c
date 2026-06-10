#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include <syslog.h>

static volatile int running = 1;

void handle_sigterm(int sig) {
    (void)sig;
    running = 0;
}

int main(void) {
    struct sigaction sa;
    sa.sa_handler = handle_sigterm;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = 0;
    sigaction(SIGTERM, &sa, NULL);

    openlog("myapp", LOG_PID | LOG_CONS, LOG_DAEMON);
    syslog(LOG_INFO, "myapp daemon starting up");
    printf("myapp daemon started\n");
    fflush(stdout);

    while (running) {
        sleep(5);
    }

    syslog(LOG_INFO, "myapp daemon shutting down gracefully");
    closelog();
    return 0;
}
