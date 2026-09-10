/* lstat metadata for configuration verification, independent of BusyBox stat. */
#include <sys/stat.h>
#include <inttypes.h>
#include <stdio.h>
int main(int argc, char **argv) {
    struct stat s;
    if (argc != 2) return 2;
    if (lstat(argv[1], &s)) { perror("lstat"); return 1; }
    printf("%jo:%ju:%ju\n", (uintmax_t)(s.st_mode & 07777),
           (uintmax_t)s.st_uid, (uintmax_t)s.st_gid);
    return 0;
}
