#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
#include <glob.h>
static int sendbyte(int fd,unsigned a,unsigned char b){struct i2c_msg m={.addr=a,.flags=I2C_M_IGNORE_NAK,.len=1,.buf=&b};struct i2c_rdwr_ioctl_data x={.msgs=&m,.nmsgs=1};if(ioctl(fd,I2C_RDWR,&x)!=1){perror("FD655 transfer");return -1;}return 0;}
int main(int argc,char **argv){
 glob_t g; int bus=-1,count=0; char path[256],name[64];
 if(glob("/sys/bus/i2c/devices/i2c-*/name",0,NULL,&g))return 2;
 for(size_t j=0;j<g.gl_pathc;j++){FILE *f=fopen(g.gl_pathv[j],"r");if(!f)continue;
 if(fgets(name,sizeof(name),f)&&!strcmp(name,"i2c-display\n")){int v;
 if(sscanf(g.gl_pathv[j],"/sys/bus/i2c/devices/i2c-%d/name",&v)==1){bus=v;count++;}}
 fclose(f);}
 globfree(&g); if(count!=1)return 2;

 if((argc!=2 && argc!=3)||strlen(argv[1])!=4)return 2;
 unsigned long mask=0x10; char *end;
 if(argc==3){errno=0;mask=strtoul(argv[2],&end,0);if(errno||!*argv[2]||*end||mask>0x7f)return 2;}
 snprintf(path,sizeof(path),"/sys/bus/i2c/devices/%d-0024/driver",bus); if(access(path,F_OK)==0)return 2;
 static const unsigned char map[]={0x3f,0x30,0x5b,0x79,0x74,0x6d,0x6f,0x38,0x7f,0x7d};
 unsigned char digits[4];
 if(!strcmp(argv[1],"boot")){digits[0]=0x67;digits[1]=0x63;digits[2]=0x63;digits[3]=0x47;}
 else for(int i=0;i<4;i++){if(argv[1][i]<'0'||argv[1][i]>'9')return 2;digits[i]=map[argv[1][i]-'0'];}
 snprintf(path,sizeof(path),"/dev/i2c-%d",bus); int fd=open(path,O_RDWR);if(fd<0){perror("FD655 open");return 1;}
 if(sendbyte(fd,0x24,0x21)||sendbyte(fd,0x33,(unsigned char)mask)){close(fd);return 1;}
 for(int i=0;i<4;i++)if(sendbyte(fd,0x34+i,digits[i])){close(fd);return 1;}
 close(fd);return 0;}
