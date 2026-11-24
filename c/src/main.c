/* Entry point for the monty-lab binary. */
#include "cli.h"

#include <signal.h>

int main(int argc, char **argv) {
    signal(SIGPIPE, SIG_IGN);
    return mh_cli_main(argc, argv, stdout, stderr);
}
