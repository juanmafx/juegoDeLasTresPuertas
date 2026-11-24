/* monty-lab command-line contract defined in spec/cli.md. */
#ifndef MH_CLI_H
#define MH_CLI_H

#include <stdio.h>

#define MH_VERSION "3.0.1"
#define MH_EXIT_OK 0
#define MH_EXIT_USAGE 2
#define MH_EXIT_BROKEN_PIPE 141

int mh_cli_main(int argc, char **argv, FILE *out, FILE *err);

#endif
