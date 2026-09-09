#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/fs.h>
#include <string.h>
int main(int argc,char **argv) {
 if(argc!=2 || strlen(argv[1])!=12 || strncmp(argv[1],"/dev/mmcblk",11) || argv[1][11]<'0' || argv[1][11]>'9') return 2;
 int fd=open(argv[1],O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
 if(fd<0){perror("open");return 3;}
 int rc=ioctl(fd,BLKRRPART);if(rc)perror("BLKRRPART");close(fd);return rc?1:0;
}
