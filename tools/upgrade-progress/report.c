#define _POSIX_C_SOURCE 200809L
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
static int sock=-1;
static struct sockaddr_in dest;
static const char *token;
static void report(const char *stage, unsigned long long bytes) {
 char msg[768];
 if(sock<0)return;
 int n=snprintf(msg,sizeof(msg),"%s\t%lld\t%s\t%llu",token,(long long)time(NULL),stage,bytes);
 if(n>0 && n<(int)sizeof(msg)) (void)sendto(sock,msg,n,MSG_DONTWAIT,(struct sockaddr*)&dest,sizeof(dest));
}
int main(int argc,char **argv) {
 if(argc!=3 || (strcmp(argv[1],"event") && strcmp(argv[1],"stream")))return 2;
 const char *ip=getenv("T95H_REPORT_IP"), *port=getenv("T95H_REPORT_PORT");token=getenv("T95H_REPORT_TOKEN");
 if(ip && port && token && strlen(token)==64) {
  char *end;long p=strtol(port,&end,10);
  memset(&dest,0,sizeof(dest));dest.sin_family=AF_INET;
  if(!*end && p>0 && p<65536 && inet_pton(AF_INET,ip,&dest.sin_addr)==1) {
   dest.sin_port=htons((unsigned short)p);sock=socket(AF_INET,SOCK_DGRAM,0);
  }
 }
 report(argv[2],0);
 if(!strcmp(argv[1],"event"))return 0;
 char buf[65536];unsigned long long total=0;time_t last=time(NULL);
 for(;;) {
  ssize_t n=read(STDIN_FILENO,buf,sizeof(buf));
  if(n<0){if(errno==EINTR)continue;perror("progress read");return 1;}
  if(!n)break;
  ssize_t off=0;
  while(off<n){ssize_t w=write(STDOUT_FILENO,buf+off,n-off);if(w<0 && errno==EINTR)continue;if(w<=0){perror("progress write");return 1;}off+=w;}
  total+=(unsigned long long)n;time_t now=time(NULL);
  if(now-last>=5){report(argv[2],total);last=now;}
 }
 report(argv[2],total);return 0;
}
