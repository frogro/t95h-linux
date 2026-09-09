// SPDX-License-Identifier: GPL-2.0-only
/* Set Linux block-device read-only state for eMMC only; never clear it.
 * Does not program persistent eMMC write-protect bits or write storage data.
 */
#define _GNU_SOURCE
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <linux/fs.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <ctype.h>

int main(int argc, char **argv) {
 char base[64], path[256], type[32], *suffix;
 struct stat st; unsigned int maj,min; int n,fd,ro=1; FILE *f;
 if(argc!=2 || strncmp(argv[1],"/dev/mmcblk",11))return 2;
 const char *name=argv[1]+5;
 if(strlen(name)>=sizeof(base) || strchr(name,'/'))return 2;
 strcpy(base,name);suffix=base+6;
 if(!isdigit(*suffix))return 2;
 while(isdigit(*suffix))suffix++;
 n=suffix-base;
 if(*suffix && strcmp(suffix,"boot0") && strcmp(suffix,"boot1")) {
  if(*suffix++!='p' || !isdigit(*suffix))return 2;
  while(isdigit(*suffix))suffix++;
  if(*suffix)return 2;
 }
 base[n]=0;
 snprintf(path,sizeof(path),"/sys/class/block/%s/device/type",base);
 f=fopen(path,"r");if(!f)return 2;
 if(!fgets(type,sizeof(type),f)){fclose(f);return 2;}fclose(f);
 if(strcmp(type,"MMC\n")){fprintf(stderr,"Refuse non-eMMC device\n");return 2;}
 snprintf(path,sizeof(path),"/sys/class/block/%s/dev",name);
 f=fopen(path,"r");if(!f)return 2;
 n=fscanf(f,"%u:%u",&maj,&min);fclose(f);if(n!=2)return 2;
 fd=open(argv[1],O_RDONLY|O_CLOEXEC|O_NOFOLLOW);if(fd<0){perror("open");return 1;}
 if(fstat(fd,&st) || !S_ISBLK(st.st_mode) || major(st.st_rdev)!=maj || minor(st.st_rdev)!=min){close(fd);return 2;}
 if(ioctl(fd,BLKROSET,&ro)){perror("BLKROSET");close(fd);return 1;}
 ro=0;if(ioctl(fd,BLKROGET,&ro) || ro!=1){close(fd);return 1;}
 close(fd);printf("READ-ONLY %s\n",argv[1]);return 0;
}
