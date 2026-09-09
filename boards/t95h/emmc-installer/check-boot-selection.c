#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <sys/ioctl.h>
#include <linux/mmc/ioctl.h>
int main(int argc,char **argv) {
 if(argc!=2 || strlen(argv[1])!=12 || strncmp(argv[1],"/dev/mmcblk",11) || argv[1][11]<'0' || argv[1][11]>'9')return 2;
 int fd=open(argv[1],O_RDONLY|O_CLOEXEC|O_NOFOLLOW);if(fd<0)return 3;
 unsigned char data[512]={0};struct mmc_ioc_cmd cmd={0};
 cmd.opcode=8;cmd.flags=1|4|16|32;cmd.blksz=512;cmd.blocks=1;mmc_ioc_cmd_set_data(cmd,data);
 int rc=ioctl(fd,MMC_IOC_CMD,&cmd);close(fd);
 if(rc){perror("read EXT_CSD");return 4;}
 if(data[179]&0x3f){fprintf(stderr,"Unsupported eMMC PARTITION_CONFIG=0x%02x; no writes performed\n",data[179]);return 5;}
 puts("PASS: eMMC user-area boot selection");return 0;
}
