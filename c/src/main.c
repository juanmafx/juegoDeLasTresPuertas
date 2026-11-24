/* Entry point for the monty-lab binary. */
#include "cli.h"
#include "rational.h"

#include <signal.h>

int main(int argc, char **argv) {
    signal(SIGPIPE, SIG_IGN);
    int code = mh_cli_main(argc, argv, stdout, stderr);
    mh_arena_release_all();
    return code;
}
